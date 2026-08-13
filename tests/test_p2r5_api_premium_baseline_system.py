"""
Regressão: `/v1/reports/premium` aceitava um `baseline_analysis` de um modelo sem relação
nenhuma e inventava a narrativa de deriva; a CLI recusava o mesmo par de artefactos.

Analisar `examples/minimal.otm.yaml` e enviá-lo como baseline de `examples/saas-ordering-v1`
devolvia 200 e um relatório de ~23 800 carateres com uma secção `## Baseline / diff` a atribuir
13 ameaças adicionadas e 6 removidas a uma revisão que nunca existiu. `otm report --baseline`,
com os mesmos dois ficheiros, sai com 1 e diz porquê.

A raiz é uma distinção que faltava no router: `baseline_analysis` está isento da guarda de
*mesma revisão* (`ensure_analysis_matches_document`) — correctamente, porque um baseline é de
outra revisão por definição — mas nunca recebeu a guarda mais fraca que a CLI aplica ao mesmo
flag, "mesmo sistema?" (`analysis_identity.system_overlap`). O comentário do router só cobria a
primeira, por isso o buraco era um esquecimento e não uma decisão.

A guarda tem de ser exatamente a fraca. Um baseline **é** outra revisão: renomear o modelo entre
releases e acrescentar componentes são as mudanças que a secção baseline/diff existe para
mostrar, e recusá-las custaria o relatório inteiro. Metade dos testes abaixo existe para fixar
isso.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402

_EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _example(name: str) -> dict[str, Any]:
    return yaml.safe_load((_EXAMPLES / name).read_text(encoding="utf-8"))


def _analysis(client: TestClient, document: dict[str, Any]) -> dict[str, Any]:
    r = client.post("/v1/models/analyze", json={"document": document})
    assert r.status_code == 200, r.text
    return r.json()


def _premium(client: TestClient, document: dict[str, Any], baseline: dict[str, Any], **extra: Any) -> Any:
    body: dict[str, Any] = {
        "document": document,
        "run_analysis": True,
        "baseline_analysis": baseline,
        "level": "deep",
    }
    body.update(extra)
    return client.post("/v1/reports/premium", json=body)


@pytest.fixture
def saas() -> dict[str, Any]:
    return _example("saas-ordering-v1.otm.yaml")


@pytest.fixture
def foreign_baseline(client: TestClient) -> dict[str, Any]:
    return _analysis(client, _example("minimal.otm.yaml"))


# --- o defeito: o baseline estrangeiro ------------------------------------------------


def test_a_foreign_baseline_is_refused(
    client: TestClient, saas: dict[str, Any], foreign_baseline: dict[str, Any]
) -> None:
    assert _premium(client, saas, foreign_baseline).status_code == 422


def test_the_refusal_carries_a_stable_code(
    client: TestClient, saas: dict[str, Any], foreign_baseline: dict[str, Any]
) -> None:
    assert _premium(client, saas, foreign_baseline).json()["detail"]["code"] == "BASELINE_SYSTEM_MISMATCH"


def test_the_refusal_does_not_reuse_the_same_revision_code(
    client: TestClient, saas: dict[str, Any], foreign_baseline: dict[str, Any]
) -> None:
    """`ANALYSIS_DOCUMENT_MISMATCH` diria "não foi produzida para este documento", o que é falso
    para um baseline e mandaria o utilizador re-correr a análise que já tem."""
    assert _premium(client, saas, foreign_baseline).json()["detail"]["code"] != "ANALYSIS_DOCUMENT_MISMATCH"


def test_the_refusal_names_the_measured_overlap(
    client: TestClient, saas: dict[str, Any], foreign_baseline: dict[str, Any]
) -> None:
    """A CLI diz "sharing 4 of the 8 structural entities"; a API tem de ser igualmente verificável."""
    errors = _premium(client, saas, foreign_baseline).json()["detail"]["errors"]

    assert "structural entities" in errors[0]["msg"]


def test_the_refusal_points_at_the_offending_field(
    client: TestClient, saas: dict[str, Any], foreign_baseline: dict[str, Any]
) -> None:
    errors = _premium(client, saas, foreign_baseline).json()["detail"]["errors"]

    assert errors[0]["loc"][:2] == ["body", "baseline_analysis"]


def test_no_report_body_is_produced(client: TestClient, saas: dict[str, Any], foreign_baseline: dict[str, Any]) -> None:
    """O dano era o artefacto: 23 809 carateres com um diff inventado, apresentado como autoridade."""
    assert "## Baseline / diff" not in _premium(client, saas, foreign_baseline).text


def test_the_guard_also_applies_with_a_supplied_analysis(
    client: TestClient, saas: dict[str, Any], foreign_baseline: dict[str, Any]
) -> None:
    """O caminho `analysis` explícito não pode ser a porta das traseiras do caminho `run_analysis`."""
    r = _premium(client, saas, foreign_baseline, run_analysis=False, analysis=_analysis(client, saas))

    assert r.status_code == 422


@pytest.mark.parametrize("level", ["executive", "standard", "deep"])
def test_the_guard_applies_at_every_level(
    client: TestClient, saas: dict[str, Any], foreign_baseline: dict[str, Any], level: str
) -> None:
    assert _premium(client, saas, foreign_baseline, level=level).status_code == 422


def test_the_api_now_agrees_with_the_cli_on_the_same_pair(
    client: TestClient, saas: dict[str, Any], foreign_baseline: dict[str, Any]
) -> None:
    """A divergência entre superfícies era o defeito; esta é a asserção que a fecha."""
    from otm_cli.application.analysis_match import require_baseline_describes_same_system
    from otm_cli.shared.errors import CliUserError
    from otm_threat_engine import AnalysisResult

    current = AnalysisResult.model_validate(_analysis(client, saas))
    baseline = AnalysisResult.model_validate(foreign_baseline)

    with pytest.raises(CliUserError):
        require_baseline_describes_same_system(current, baseline, flag="--baseline")
    assert _premium(client, saas, foreign_baseline).status_code == 422


# --- o que não pode partir: um baseline é outra revisão, e isso é normal --------------


def test_the_models_own_earlier_analysis_is_accepted(client: TestClient, saas: dict[str, Any]) -> None:
    assert _premium(client, saas, _analysis(client, saas)).status_code == 200


def test_the_accepted_baseline_still_produces_the_diff_section(client: TestClient, saas: dict[str, Any]) -> None:
    """Recusar de mais custaria exatamente a funcionalidade que o flag existe para dar."""
    assert "Baseline" in _premium(client, saas, _analysis(client, saas)).text


def test_a_renamed_model_still_accepts_its_own_baseline(client: TestClient, saas: dict[str, Any]) -> None:
    """Renomear entre releases é banal, e foi o que partiu a primeira tentativa de guarda."""
    renamed = copy.deepcopy(saas)
    renamed["metadata"]["title"] = "Ordering platform (2026 rebrand)"

    assert _premium(client, renamed, _analysis(client, saas)).status_code == 200


def test_a_grown_model_still_accepts_its_earlier_baseline(client: TestClient, saas: dict[str, Any]) -> None:
    """Acrescentar componentes é a mudança que um baseline existe para mostrar."""
    baseline = _analysis(client, saas)
    grown = copy.deepcopy(saas)
    grown["components"].append({"id": "new_worker", "name": "New worker", "kind": "process"})

    assert _premium(client, grown, baseline).status_code == 200


def test_a_grown_and_renamed_model_is_still_accepted(client: TestClient, saas: dict[str, Any]) -> None:
    """As duas mudanças ao mesmo tempo: o caso real de uma release."""
    baseline = _analysis(client, saas)
    next_revision = copy.deepcopy(saas)
    next_revision["metadata"]["title"] = "Ordering platform (2026 rebrand)"
    next_revision["components"].append({"id": "new_worker", "name": "New worker", "kind": "process"})

    assert _premium(client, next_revision, baseline).status_code == 200


def test_the_grown_model_report_still_carries_the_diff(client: TestClient, saas: dict[str, Any]) -> None:
    baseline = _analysis(client, saas)
    grown = copy.deepcopy(saas)
    grown["components"].append({"id": "new_worker", "name": "New worker", "kind": "process"})

    assert "Baseline" in _premium(client, grown, baseline).text


def test_a_report_without_a_baseline_is_untouched(client: TestClient, saas: dict[str, Any]) -> None:
    r = client.post("/v1/reports/premium", json={"document": saas, "run_analysis": True, "level": "deep"})

    assert r.status_code == 200


def test_an_invalid_baseline_payload_still_answers_analysis_validation_error(
    client: TestClient, saas: dict[str, Any]
) -> None:
    """A guarda nova corre depois da validação: um baseline mal formado tem o seu próprio erro."""
    r = _premium(client, saas, {"not": "an analysis"})

    assert r.json()["detail"]["code"] == "ANALYSIS_VALIDATION_ERROR"
