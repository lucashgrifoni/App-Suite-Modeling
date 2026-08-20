"""O resumo não pode afirmar "sem findings" quando o scan não correu.

`Report dev-dependency findings` corre com `if: always()` — de propósito, para que o resumo
apareça mesmo quando o passo anterior falha. O teste que faltava é o de o passo saber **porquê**
não há ficheiro. `[ -s trivy-dev-deps.txt ]` é falso em dois estados diferentes:

* o trivy correu e não encontrou nada — "sem findings" é verdade;
* o trivy não correu de todo (binário ausente, erro de invocação, rede) — "sem findings" é uma
  afirmação de segurança sobre uma verificação que nunca aconteceu.

O passo do scan já distingue os dois casos e está comentado a dizê-lo: recusa `continue-on-error`
precisamente para separar "não há nada" de "não corremos". Essa distinção perdia-se uma linha
abaixo, no artefacto que uma pessoa lê como evidência de release.

O job falha na mesma quando o scan falha, portanto isto não deixava passar um merge; deixava um
registo falso na evidência, que é o que estes resumos existem para ser.
"""

from __future__ import annotations

import pathlib

import pytest
from test_cicd_pipeline_invariants import (
    BASH,
    SECURITY_WF,
    _actions_env,
    _run_bash,
    _step,
)

pytestmark = pytest.mark.skipif(BASH is None, reason="precisa de uma shell POSIX")

_JOB = "sca-trivy"
_STEP = "Report dev-dependency findings"
_ENV = {"TRIVY_SEVERITY": "MEDIUM,HIGH,CRITICAL"}


def _summary_for(tmp_path: pathlib.Path, *, report: str | None) -> str:
    """`report=None` é o scan que não correu; `""` é o scan que correu e não achou nada."""
    if report is not None:
        (tmp_path / "trivy-dev-deps.txt").write_text(report, encoding="utf-8")
    env = _actions_env(tmp_path) | _ENV
    result = _run_bash(_step(SECURITY_WF, _JOB, _STEP)["run"], env, tmp_path)
    assert result.returncode == 0, result.stderr
    return pathlib.Path(env["GITHUB_STEP_SUMMARY"]).read_text(encoding="utf-8")


def test_o_scan_que_correu_sem_achados_diz_sem_findings(tmp_path: pathlib.Path) -> None:
    summary = _summary_for(tmp_path, report="")

    assert "Sem findings" in summary, summary


def test_o_scan_que_nao_correu_nao_pode_afirmar_sem_findings(tmp_path: pathlib.Path) -> None:
    summary = _summary_for(tmp_path, report=None)

    assert "Sem findings" not in summary, (
        "o resumo afirma ausência de vulnerabilidades sobre um scan que nunca correu:\n" + summary
    )
    assert "não correu" in summary or "not run" in summary.lower(), (
        "o resumo tem de dizer que o scan não produziu resultado:\n" + summary
    )


def test_o_scan_com_achados_mostra_o_relatorio(tmp_path: pathlib.Path) -> None:
    summary = _summary_for(tmp_path, report="CVE-2026-0001  HIGH  requests\n")

    assert "CVE-2026-0001" in summary, summary
    assert "Sem findings" not in summary, summary
