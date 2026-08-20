"""O veredito do gate não pode ser decidido por texto que o autor do modelo escreve.

O passo do gate classifica o resultado com `grep -q "NOT EVALUATED"` sobre o relatório do CLI, e
o relatório cita o `metadata.title` do modelo — campo de texto livre, sem padrão nem tecto, que o
`otm validate` aceita. Quem abre a pull request é exactamente quem o gate existe para julgar.

Medido na captura que a Action faz (`2>&1 1>/dev/null`, só stderr), com um modelo que introduz uma
regressão real (fluxo público sem autenticação nem cifra) **e** tem `metadata.title: NOT EVALUATED`:

    regressão real, título normal    rc=3   casa com "NOT EVALUATED": não
    regressão real, título forjado   rc=3   casa com "NOT EVALUATED": SIM
    recusa genuína de veredito       rc=1   casa: sim, e no início de linha

Nos dois primeiros o gate reprovou. No segundo, a Action anunciava `gate-outcome=not-evaluated` e
dizia ao operador que **nada foi julgado**, com conselho de remediação para uma troca de lente que
não houve — no mesmo resumo que lista a ameaça nova. A build falha em ambos os casos, por isso não
é um contorno do gate; o que se corrompe é o output que outros jobs consomem e a explicação que a
pessoa lê.

Duas defesas: o marcador passa a ser ancorado ao início da linha (`THREAT MODEL GATE: NOT
EVALUATED`, que o CLI escreve e um título não consegue produzir, porque um título só aparece
dentro da frase de resumo), e a verificação passa para dentro do ramo `rc=1` — um gate reprovado
é `3` e deixa de poder ser reclassificado seja qual for o texto.
"""

from __future__ import annotations

import copy
import pathlib
import re
import subprocess
import sys

import pytest
import yaml
from test_cicd_pipeline_invariants import SECURITY_WF, _step  # noqa: F401  (reutiliza o localizador)

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_ACTION = _ROOT / "action.yml"
_ANCHOR = "THREAT MODEL GATE: NOT EVALUATED"


def _gate_step() -> dict:
    steps = yaml.safe_load(_ACTION.read_text(encoding="utf-8"))["runs"]["steps"]
    return next(s for s in steps if s.get("id") == "gate")


def _models(tmp_path: pathlib.Path) -> dict[str, pathlib.Path]:
    source = yaml.safe_load((_ROOT / "examples" / "minimal.otm.yaml").read_text(encoding="utf-8"))
    out: dict[str, pathlib.Path] = {}

    worse = copy.deepcopy(source)
    worse["data_flows"][0].update({"protocol": "HTTP", "authenticated": False, "encrypted": False})
    hijack = copy.deepcopy(worse)
    hijack["metadata"]["title"] = "NOT EVALUATED"

    for name, doc in (("base", source), ("worse", worse), ("hijack", hijack)):
        path = tmp_path / f"{name}.otm.yaml"
        path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        out[name] = path
    return out


def _gate(baseline: pathlib.Path, revised: pathlib.Path) -> tuple[str, int]:
    """(relatório, código) exactamente como a Action os captura: só stderr."""
    proc = subprocess.run(  # noqa: S603 - argv fixo, sem shell
        [sys.executable, "-m", "otm_cli.main", "diff", str(baseline), str(revised), "--fail-on", "high"],
        capture_output=True,
        text=True,
        cwd=str(_ROOT),
    )
    return proc.stderr, proc.returncode


@pytest.fixture(scope="module")
def models(tmp_path_factory: pytest.TempPathFactory) -> dict[str, pathlib.Path]:
    return _models(tmp_path_factory.mktemp("gate"))


def test_o_titulo_forjado_e_aceite_pelo_schema(models: dict[str, pathlib.Path]) -> None:
    """Sanidade: se o schema o recusasse, não haveria caminho para aqui."""
    doc = yaml.safe_load(models["hijack"].read_text(encoding="utf-8"))

    assert doc["metadata"]["title"] == "NOT EVALUATED"


def test_a_regressao_reprova_o_gate_com_ou_sem_o_titulo(models: dict[str, pathlib.Path]) -> None:
    """A premissa: os dois modelos reprovam, portanto o `rc` distingue-os de uma recusa."""
    for name in ("worse", "hijack"):
        _, code = _gate(models["base"], models[name])
        assert code == 3, f"{name} devia reprovar o gate, deu {code}"


def test_o_marcador_ancorado_nao_casa_com_o_titulo(models: dict[str, pathlib.Path]) -> None:
    report, _ = _gate(models["base"], models["hijack"])

    assert "NOT EVALUATED" in report, "premissa: o título aparece mesmo no relatório"
    anchored = [line for line in report.splitlines() if line.startswith(_ANCHOR)]
    assert not anchored, f"o título produziu o marcador do CLI: {anchored}"


def test_a_recusa_genuina_produz_o_marcador_ancorado(tmp_path: pathlib.Path) -> None:
    source = yaml.safe_load((_ROOT / "examples" / "minimal.otm.yaml").read_text(encoding="utf-8"))
    paths = []
    for name, lens in (("a", "stride"), ("b", "linddun")):
        doc = copy.deepcopy(source)
        doc["model"]["methodology"] = lens
        path = tmp_path / f"{name}.otm.yaml"
        path.write_text(yaml.safe_dump(doc, allow_unicode=True, sort_keys=False), encoding="utf-8")
        paths.append(path)

    report, code = _gate(paths[0], paths[1])

    assert code == 1, report[:200]
    assert any(line.startswith(_ANCHOR) for line in report.splitlines()), report[:400]


def test_a_action_ancora_o_marcador_e_so_o_procura_quando_nao_ha_veredito() -> None:
    run = _gate_step()["run"]

    match = re.search(r'grep -q(?P<flags>E?) "(?P<pattern>[^"]*NOT EVALUATED[^"]*)"', run)
    assert match, f"não encontrei a deteção do não-veredito no passo:\n{run[:400]}"
    assert match.group("pattern").startswith("^"), (
        f"o padrão `{match.group('pattern')}` casa em qualquer sítio do relatório, "
        "e o relatório cita o título do modelo"
    )
    before = run[: match.start()]
    assert "case " in before and '"${rc}"' in before, (
        "a deteção corre antes do `case` do código de saída, por isso pode reclassificar um gate "
        "reprovado (rc=3) como não-avaliado"
    )
