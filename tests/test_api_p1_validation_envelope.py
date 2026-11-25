"""
Regressão: o handler de `RequestValidationError` tem de produzir sempre um 422 serializável.

Pydantic guarda o objeto ``Exception`` original em ``ctx['error']`` para validadores
customizados (`@model_validator` que faz `raise ValueError(...)`). Esse objeto não é
serializável em JSON: se chegar ao `JSONResponse`, o `json.dumps` rebenta *dentro* do
próprio handler de 422 e o cliente recebe um 500 `INTERNAL_ERROR` genérico — perdendo
a mensagem acionável que o validador escreveu.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from otm_core_schema import load_document_from_yaml_path

pytest.importorskip("fastapi")
from fastapi.exceptions import RequestValidationError  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.errors import request_validation_handler  # noqa: E402
from otm_api.main import app  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _doc() -> dict[str, Any]:
    return load_document_from_yaml_path(_MINIMAL).model_dump(mode="json", by_alias=True)


def test_compare_with_only_one_analysis_returns_422_not_500(client: TestClient) -> None:
    """`CompareBody._pair_analyses` existe para rejeitar este caso — tem de chegar ao cliente."""
    d = _doc()
    r = client.post(
        "/v1/models/compare",
        json={"baseline": d, "revised": d, "baseline_analysis": {"any": "payload"}},
    )
    assert r.status_code == 422, r.text
    body = r.json()
    assert body["code"] == "REQUEST_VALIDATION_ERROR"
    # A mensagem do validador é o valor útil da resposta: não pode ser descartada.
    assert "baseline_analysis" in json.dumps(body, ensure_ascii=False)


@pytest.mark.parametrize("route", ["openapi", "terraform", "kubernetes"])
def test_import_routes_reject_text_file_field_with_422(client: TestClient, route: str) -> None:
    """`file` enviado como campo de texto (erro comum de curl/Postman) é erro de cliente."""
    r = client.post(f"/v1/imports/{route}", data={"file": "openapi: 3.0.0"})
    assert r.status_code == 422, r.text
    assert r.json()["code"] == "REQUEST_VALIDATION_ERROR"


def test_handler_renders_exception_in_ctx_as_json() -> None:
    """Unidade: um `Exception` em `ctx` não pode impedir a renderização do 422."""
    exc = RequestValidationError(
        [
            {
                "type": "value_error",
                "loc": ("body",),
                "msg": "Value error, boom",
                "input": {"a": 1},
                "ctx": {"error": ValueError("boom")},
            }
        ]
    )
    response = request_validation_handler(None, exc)  # type: ignore[arg-type]
    assert response.status_code == 422
    payload = json.loads(response.body)
    assert payload["code"] == "REQUEST_VALIDATION_ERROR"
    # O erro sobrevive como texto em vez de rebentar a serialização.
    assert payload["errors"][0]["ctx"]["error"] == "boom"
