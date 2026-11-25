"""
Regressão: o contrato tem de declarar o perímetro que o middleware aplica.

O perímetro de `OTM_API_KEY` está implementado como middleware ASGI puro, que o FastAPI não
vê — por isso o `openapi.json` não trazia `components.securitySchemes`, nenhuma das 17
operações `/v1` declarava `security`, e a consequência era prática, não cosmética: o Swagger
UI que a própria rota raiz anuncia (`"docs": "/docs"`) não mostrava botão **Authorize**, e
qualquer SDK gerado a partir do contrato saía sem forma de enviar a credencial.

A correção declara o que o middleware já aceita — `X-OTM-API-Key` **ou**
`Authorization: Bearer` — e nada mais: com `auto_error=False` as dependências documentam os
esquemas sem decidir nada, por isso o ponto de aplicação continua a ser o middleware. É essa
a fronteira que estes testes fixam nos dois sentidos: o contrato não pode ficar aquém do que
é aplicado, e não pode passar a recusar o que hoje é aceite.
"""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402

_KEY = "p3-openapi-contract-secret"
_ENVS = ["OTM_ENV", "OTM_CORS_ORIGINS", "OTM_API_KEY", "OTM_RATE_LIMIT", "OTM_RATE_LIMIT_DISABLED"]


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ENVS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def spec() -> dict[str, Any]:
    return app.openapi()


def _schemes(spec: dict[str, Any]) -> dict[str, Any]:
    return spec.get("components", {}).get("securitySchemes", {})


def _v1_operations(spec: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    return [
        (path, method, operation)
        for path, operations in spec["paths"].items()
        if path.startswith("/v1")
        for method, operation in operations.items()
    ]


# --- o contrato declara o esquema -------------------------------------------------------


def test_the_contract_declares_the_api_key_header_scheme(spec: dict[str, Any]) -> None:
    """O sintoma original: `components.securitySchemes` ausente por completo."""
    assert any(
        s.get("type") == "apiKey" and s.get("in") == "header" and s.get("name") == "X-OTM-API-Key"
        for s in _schemes(spec).values()
    ), _schemes(spec)


def test_the_contract_declares_the_bearer_scheme_the_middleware_also_accepts(spec: dict[str, Any]) -> None:
    """Declarar só um dos dois deixava metade do que é aceite fora do contrato."""
    bearer = [s for s in _schemes(spec).values() if s.get("type") == "http"]

    assert [s.get("scheme") for s in bearer] == ["bearer"]


def test_every_declared_scheme_says_when_it_is_required(spec: dict[str, Any]) -> None:
    """O perímetro é opcional; um contrato que o declare sem o dizer é uma meia-verdade."""
    assert all("OTM_API_KEY" in (s.get("description") or "") for s in _schemes(spec).values())


def test_every_enforced_operation_declares_security(spec: dict[str, Any]) -> None:
    undeclared = [f"{method.upper()} {path}" for path, method, op in _v1_operations(spec) if not op.get("security")]

    assert undeclared == []


def test_the_v1_surface_under_test_is_the_whole_surface(spec: dict[str, Any]) -> None:
    """Se o número mudar, alguém acrescentou rotas — e este ficheiro tem de as ver."""
    assert len(_v1_operations(spec)) == 17


def test_both_credentials_are_offered_as_alternatives(spec: dict[str, Any]) -> None:
    """`[{A: []}, {B: []}]` é "um **ou** o outro" — que é o que o middleware faz."""
    _, _, operation = _v1_operations(spec)[0]

    assert len(operation["security"]) == 2


# --- e não declara o que não é aplicado -------------------------------------------------


@pytest.mark.parametrize("path", ["/", "/health"])
def test_open_routes_declare_no_security(spec: dict[str, Any], path: str) -> None:
    """`/health` e `/` nunca exigem chave; declará-las protegidas seria a mentira simétrica."""
    assert all(not operation.get("security") for operation in spec["paths"][path].values())


def test_no_operation_gained_a_required_parameter(spec: dict[str, Any]) -> None:
    """A credencial é um esquema de segurança, não um parâmetro obrigatório do pedido."""
    required_headers = [
        f"{method.upper()} {path}:{parameter['name']}"
        for path, method, operation in _v1_operations(spec)
        for parameter in operation.get("parameters", [])
        if parameter.get("in") == "header" and parameter.get("required")
    ]

    assert required_headers == []


# --- o contrato descreve o que a app faz ------------------------------------------------


def _header_scheme(spec: dict[str, Any]) -> dict[str, Any]:
    return next(s for s in _schemes(spec).values() if s.get("type") == "apiKey")


def test_the_documented_header_really_authenticates(spec: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> None:
    """O nome do cabeçalho vem do contrato, não do teste: se divergir do middleware, falha."""
    monkeypatch.setenv("OTM_API_KEY", _KEY)
    header = _header_scheme(spec)["name"]

    r = TestClient(app).get("/v1/templates", headers={header: _KEY})

    assert r.status_code == 200, r.text


def test_the_documented_bearer_scheme_really_authenticates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_API_KEY", _KEY)

    r = TestClient(app).get("/v1/templates", headers={"Authorization": f"Bearer {_KEY}"})

    assert r.status_code == 200, r.text


def test_the_enforcement_point_did_not_move(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem credencial continua a ser o 401 do middleware — não o 403 do FastAPI."""
    monkeypatch.setenv("OTM_API_KEY", _KEY)

    r = TestClient(app).get("/v1/templates")

    assert r.status_code == 401


def test_the_rejection_keeps_the_documented_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_API_KEY", _KEY)

    body = TestClient(app).get("/v1/templates").json()

    assert body["code"] == "API_KEY_REQUIRED"


# --- a recusa que esta correção **não** pode introduzir ---------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/v1/templates"),
        ("POST", "/v1/models"),
        ("POST", "/v1/models/validate"),
        ("POST", "/v1/templates/admin-portal/instantiate"),
    ],
)
def test_the_open_default_posture_still_needs_no_credential(method: str, path: str) -> None:
    """
    A armadilha desta correção, fixada.

    `APIKeyHeader(auto_error=True)` — o default — responde 403 quando o cabeçalho falta,
    **dentro** da rota e independentemente de `OTM_API_KEY`. Isso partiria o modo por omissão
    do produto (API aberta, documentado em `DEPLOYMENT_INVARIANTS.md`) em todas as 17
    operações, trocando um perímetro em falta por um perímetro que ninguém pode satisfazer.
    """
    r = TestClient(app).request(method, path, json={} if method == "POST" else None)

    assert r.status_code != 403, r.text


def test_an_unknown_authorization_scheme_is_still_not_a_403() -> None:
    """`Authorization: Basic ...` com o perímetro desligado continua a ser um pedido normal."""
    r = TestClient(app).get("/v1/templates", headers={"Authorization": "Basic Zm9vOmJhcg=="})

    assert r.status_code == 200, r.text


def test_the_committed_contract_carries_the_scheme() -> None:
    """`contracts/openapi.json` é o que gera os clientes; um esquema só em runtime não serve."""
    import json
    from pathlib import Path

    committed = json.loads(
        (Path(__file__).resolve().parents[1] / "contracts" / "openapi.json").read_text(encoding="utf-8")
    )

    assert _schemes(committed)
