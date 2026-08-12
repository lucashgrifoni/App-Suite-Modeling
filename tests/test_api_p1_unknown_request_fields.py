"""
Regressão: um campo desconhecido no corpo do pedido é 422, não é ignorado em silêncio.

Porquê recusar em vez de ignorar (o default do Pydantic): a saída deste produto é uma
*afirmação de cobertura de segurança*. Com `extra="ignore"`, `pack` em vez de `pack_id`
devolvia 200 com menos ameaças, e `format` em vez de `formats` devolvia 200 com um
artefacto diferente do pedido — em ambos os casos sem nada na resposta a indicar que o
campo foi descartado. Um valor errado (`pack_id: "nope"`) já falhava alto com 404; só a
*chave* errada falhava em silêncio.

É a mesma regra que o projeto já aplica ao documento canónico (que recusa extras) e às
regras customizadas (`otm_threat_engine.custom_rules.models`, que documenta o campo
mal escrito como "o pior modo de falha possível").
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from otm_core_schema import load_document_from_yaml_path

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _doc() -> dict[str, Any]:
    return load_document_from_yaml_path(_MINIMAL).model_dump(mode="json", by_alias=True)


def _assert_rejects_field(r: Any, field: str) -> None:
    assert r.status_code == 422, f"expected 422, got {r.status_code}: {r.text[:200]}"
    body = r.json()
    assert body["code"] == "REQUEST_VALIDATION_ERROR"
    # A resposta tem de nomear a chave ofensora, senão não é acionável.
    offending = [e for e in body["errors"] if field in e.get("loc", [])]
    assert offending, f"{field} not named in {body['errors']}"
    assert offending[0]["type"] == "extra_forbidden"


def test_analyze_rejects_pack_typo(client: TestClient) -> None:
    """`pack` em vez de `pack_id` — silenciosamente perdia as ameaças do industry pack."""
    r = client.post("/v1/models/analyze", json={"document": _doc(), "pack": "finance"})
    _assert_rejects_field(r, "pack")


def test_exports_rejects_format_typo(client: TestClient) -> None:
    """`format` em vez de `formats` — devolvia `document_json` em vez do pedido."""
    r = client.post("/v1/exports", json={"document": _doc(), "format": "document_markdown"})
    _assert_rejects_field(r, "format")


def test_compare_rejects_unknown_field(client: TestClient) -> None:
    d = _doc()
    r = client.post("/v1/models/compare", json={"baseline": d, "revised": d, "run_analysys": True})
    _assert_rejects_field(r, "run_analysys")


def test_remediation_backlog_rejects_unknown_field(client: TestClient) -> None:
    r = client.post("/v1/remediation/backlog", json={"document": _doc(), "packid": "saas"})
    _assert_rejects_field(r, "packid")


def test_premium_report_rejects_unknown_field(client: TestClient) -> None:
    r = client.post("/v1/reports/premium", json={"document": _doc(), "run_analysis": True, "levl": "deep"})
    _assert_rejects_field(r, "levl")


def test_analyses_diff_rejects_unknown_field(client: TestClient) -> None:
    r = client.post(
        "/v1/analyses/diff",
        json={"baseline_analysis": {}, "revised_analysis": {}, "extra": 1},
    )
    _assert_rejects_field(r, "extra")


# --- controlos: os campos legítimos continuam a funcionar ---


def test_correct_field_names_still_succeed(client: TestClient) -> None:
    d = _doc()
    assert client.post("/v1/models/analyze", json={"document": d, "pack_id": "finance"}).status_code == 200
    r = client.post("/v1/exports", json={"document": d, "formats": ["document_markdown"]})
    assert r.status_code == 200
    assert list(r.json()["artifacts"]) == ["document_markdown"]


def test_pack_id_still_changes_the_result(client: TestClient) -> None:
    """Mantém observável o downgrade silencioso que motivou esta regra."""
    d = _doc()
    with_pack = client.post("/v1/models/analyze", json={"document": d, "pack_id": "finance"}).json()
    without = client.post("/v1/models/analyze", json={"document": d}).json()
    assert len(with_pack["heuristic_threats"]) > len(without["heuristic_threats"])
    assert with_pack["industry_pack_id"] == "finance"
    assert without["industry_pack_id"] is None


def test_nested_document_dict_is_not_affected(client: TestClient) -> None:
    """`document` é um passthrough `dict[str, Any]`; a validação é do schema canónico.

    Recusar extras no envelope não pode alterar a mensagem de erro do documento.
    """
    bad = _doc()
    bad["nao_existe_no_schema"] = 1
    r = client.post("/v1/models/analyze", json={"document": bad})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "DOCUMENT_VALIDATION_ERROR"
