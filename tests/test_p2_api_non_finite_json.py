"""
Regressão: `NaN` / `Infinity` no corpo do pedido não pode virar 500.

`json.dumps` da stdlib emite `NaN` para um float NaN por omissão, por isso um cliente
Python normal envia o literal sem fazer nada de exótico. O valor chega ao handler de 422
dentro de `errors["input"]`; o `JSONResponse` do Starlette serializa com `allow_nan=False`
e rebentava *dentro* do próprio handler — o cliente recebia `INTERNAL_ERROR` genérico em
vez do 422 documentado, em todas as rotas com corpo JSON.
"""

from __future__ import annotations

import json
from typing import Any

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.errors import _truncate  # noqa: E402
from otm_api.main import app  # noqa: E402

_JSON = {"content-type": "application/json"}

_NON_FINITE_BODIES = [
    ("/v1/models/validate", '{"document": {"metadata": {"title": NaN}}}'),
    ("/v1/models/precheck", '{"document": {"metadata": {"title": Infinity}}}'),
    ("/v1/models/analyze", '{"document": {}, "methodology": NaN}'),
    ("/v1/models/diff", '{"baseline": {}, "revised": {"x": Infinity}}'),
    ("/v1/models/compare", '{"baseline": {}, "revised": {"x": -Infinity}}'),
    ("/v1/models/recommend-methodology", '{"document": {"a": NaN}}'),
    ("/v1/analyses/diff", '{"baseline_analysis": {"a": NaN}, "revised_analysis": {}}'),
    ("/v1/exports", '{"document": {"a": NaN}}'),
    ("/v1/remediation/backlog", '{"document": {"a": -Infinity}}'),
    ("/v1/reports/premium", '{"document": {"a": NaN}}'),
]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _envelope(response_text: str) -> dict[str, Any]:
    """O 422 chega como envelope de topo (`RequestValidationError`) ou dentro de `detail`."""
    body = json.loads(response_text)
    inner = body.get("detail")
    return inner if isinstance(inner, dict) else body


@pytest.mark.parametrize(("path", "body"), _NON_FINITE_BODIES)
def test_non_finite_literal_never_returns_500(client: TestClient, path: str, body: str) -> None:
    r = client.post(path, content=body, headers=_JSON)
    assert r.status_code == 422, r.text


@pytest.mark.parametrize(("path", "body"), _NON_FINITE_BODIES)
def test_non_finite_literal_keeps_the_field_level_errors(client: TestClient, path: str, body: str) -> None:
    """O 422 tem de continuar a nomear o campo — é o valor útil da resposta."""
    envelope = _envelope(client.post(path, content=body, headers=_JSON).text)
    assert envelope["errors"]


def test_nan_in_an_unknown_field_names_that_field(client: TestClient) -> None:
    r = client.post("/v1/models/validate", content='{"document": {}, "bogus": NaN}', headers=_JSON)
    assert "bogus" in r.text


def test_realistic_python_client_payload_is_a_422(client: TestClient) -> None:
    """`json.dumps` com um float NaN — o caminho por onde isto chega na prática."""
    body = json.dumps({"document": {"metadata": {"title": "t", "document_version": float("nan")}}})
    r = client.post("/v1/models/validate", content=body, headers=_JSON)
    assert r.status_code == 422, r.text


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (float("nan"), "NaN"),
        (float("inf"), "Infinity"),
        (float("-inf"), "-Infinity"),
    ],
)
def test_truncate_renders_non_finite_floats_as_text(value: float, expected: str) -> None:
    assert _truncate(value) == expected


@pytest.mark.parametrize("value", [0, 1.5, -2.5, True, None])
def test_truncate_still_passes_finite_scalars_through(value: object) -> None:
    assert _truncate(value) is value


def test_truncate_output_is_serializable_with_allow_nan_disabled() -> None:
    """O `JSONResponse` serializa com `allow_nan=False`; nada pode sair daqui que rebente."""
    cleaned = _truncate({"a": [float("nan"), float("inf")], "b": {"c": float("-inf")}})
    assert json.dumps(cleaned, allow_nan=False)
