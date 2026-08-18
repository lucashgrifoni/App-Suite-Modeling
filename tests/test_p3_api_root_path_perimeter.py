"""
Regressão: o perímetro de chave de API tem de gatilhar no **mesmo caminho** em que o router
resolve a rota.

O defeito: `OptionalApiKeyMiddleware` decidia a partir de `request.url.path`, que é
`scope["path"]` — o caminho na rede, **com** o prefixo de `root_path`. O router do Starlette
resolve com `get_route_path(scope)`, que **remove** esse prefixo antes de casar. Qualquer
`root_path` não vazio caía entre os dois: o prefixo derrotava o `startswith("/v1")` do
middleware, e a rota continuava a casar e a executar.

O gatilho é o deployment em sub-caminho que o FastAPI documenta — um proxy que **corta** o
prefixo (`proxy_pass http://api:8000/;`) mais `uvicorn --root-path /api`, que é exatamente o
prefixo que o cliente web deste repositório usa por omissão (`VITE_API_PREFIX ?? "/api"`).
O uvicorn constrói `scope["path"] = root_path + path` (ver `h11_impl`/`httptools_impl`), por
isso o `TestClient(app, root_path=...)` reproduz a mesma forma de scope que o servidor real.

Medido antes da correção, com `OTM_API_KEY` definida e o arranque a escrever
`api_key=enforced`: **todas** as 17 operações `/v1` respondiam sem credencial nenhuma, e uma
chave deliberadamente errada também recebia 200.
"""

from __future__ import annotations

from typing import Any

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api import middleware_api_key  # noqa: E402
from starlette.routing import get_route_path  # noqa: E402

_KEY = "p3-root-path-perimeter-secret"
_ROOT = "/api"
_ENVS = ["OTM_ENV", "OTM_CORS_ORIGINS", "OTM_API_KEY", "OTM_RATE_LIMIT", "OTM_RATE_LIMIT_DISABLED"]


@pytest.fixture(autouse=True)
def _enforced_perimeter(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ENVS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("OTM_API_KEY", _KEY)


@pytest.fixture
def behind_proxy() -> TestClient:
    """A app como o uvicorn a serve com `--root-path /api`: prefixo em `scope["path"]`."""
    from otm_api.main import app

    return TestClient(app, root_path=_ROOT)


@pytest.fixture
def direct() -> TestClient:
    """A mesma app sem `root_path` — o controlo que já estava correto."""
    from otm_api.main import app

    return TestClient(app)


# --- o defeito: /v1 servido sem credencial sob root_path -------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", f"{_ROOT}/v1/templates"),
        ("POST", f"{_ROOT}/v1/models"),
        ("POST", f"{_ROOT}/v1/models/analyze"),
        ("POST", f"{_ROOT}/v1/models/validate"),
        ("POST", f"{_ROOT}/v1/models/compare"),
        ("POST", f"{_ROOT}/v1/reports/premium"),
        ("POST", f"{_ROOT}/v1/remediation/backlog"),
        ("POST", f"{_ROOT}/v1/exports"),
        ("POST", f"{_ROOT}/v1/analyses/diff"),
        ("POST", f"{_ROOT}/v1/templates/admin-portal/instantiate"),
    ],
)
def test_v1_under_a_root_path_requires_the_key(behind_proxy: TestClient, method: str, path: str) -> None:
    """O sintoma original: 200/201, motor executado, sem chave nenhuma."""
    r = behind_proxy.request(method, path, json={} if method == "POST" else None)

    assert r.status_code == 401, f"{method} {path} -> {r.status_code}"


def test_a_wrong_key_under_a_root_path_is_rejected(behind_proxy: TestClient) -> None:
    """Sem isto, "fechado" seria só "fechado contra quem não tenta"."""
    r = behind_proxy.get(f"{_ROOT}/v1/templates", headers={"X-OTM-API-Key": "TOTALLY-WRONG"})

    assert r.status_code == 401


def test_the_rejection_under_a_root_path_carries_the_documented_code(behind_proxy: TestClient) -> None:
    body: dict[str, Any] = behind_proxy.get(f"{_ROOT}/v1/templates").json()

    assert body["code"] == "API_KEY_REQUIRED"


# --- e o que **não** pode passar a ser recusado ----------------------------------------


def test_the_right_key_still_works_under_a_root_path(behind_proxy: TestClient) -> None:
    """A guarda contra falsos aceites não pode virar recusa de quem tem a credencial."""
    r = behind_proxy.get(f"{_ROOT}/v1/templates", headers={"X-OTM-API-Key": _KEY})

    assert r.status_code == 200, r.text


def test_the_bearer_form_still_works_under_a_root_path(behind_proxy: TestClient) -> None:
    r = behind_proxy.get(f"{_ROOT}/v1/templates", headers={"Authorization": f"Bearer {_KEY}"})

    assert r.status_code == 200, r.text


@pytest.mark.parametrize("path", [f"{_ROOT}/health", f"{_ROOT}/docs", f"{_ROOT}/openapi.json", f"{_ROOT}/"])
def test_unversioned_routes_stay_open_under_a_root_path(behind_proxy: TestClient, path: str) -> None:
    """`/health`, `/docs`, `/openapi.json` e `/` nunca exigiram chave — e continuam a não exigir."""
    r = behind_proxy.get(path)

    assert r.status_code == 200, f"{path} -> {r.status_code}"


def test_options_stays_exempt_under_a_root_path(behind_proxy: TestClient) -> None:
    """`OPTIONS` é o preflight do browser: um 401 aqui parte o CORS antes do pedido real."""
    r = behind_proxy.options(
        f"{_ROOT}/v1/models/validate",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type, x-otm-api-key",
        },
    )

    assert r.status_code == 200, r.text


def test_the_direct_deployment_is_unchanged_without_a_key(direct: TestClient) -> None:
    assert direct.get("/v1/templates").status_code == 401


def test_the_direct_deployment_is_unchanged_with_the_key(direct: TestClient) -> None:
    assert direct.get("/v1/templates", headers={"X-OTM-API-Key": _KEY}).status_code == 200


def test_health_is_unchanged_on_the_direct_deployment(direct: TestClient) -> None:
    assert direct.get("/health").status_code == 200


def test_an_unprefixed_call_to_a_root_path_deployment_is_still_gated(behind_proxy: TestClient) -> None:
    """Um caminho que não traz o prefixo é resolvido tal como está — e é `/v1`, logo é gatilhado."""
    r = behind_proxy.get("/v1/templates")

    assert r.status_code == 401


# --- a fonte do caminho, fixada contra o Starlette instalado ---------------------------


def test_the_perimeter_uses_the_same_path_source_as_the_router() -> None:
    """
    O acoplamento que a correção introduz, escrito como teste.

    `get_route_path` vive em `starlette._utils` e é reexportado por `starlette.routing`, que é
    o módulo público onde o próprio `Router` o consome. Se uma versão futura mudar o nome ou o
    sítio, isto falha aqui — em vez de o perímetro voltar a divergir do router em silêncio,
    que é exatamente o defeito que esta correção fecha.
    """
    assert middleware_api_key.get_route_path is get_route_path


@pytest.mark.parametrize(
    ("scope", "expected"),
    [
        ({"path": "/v1/templates", "root_path": ""}, "/v1/templates"),
        ({"path": "/api/v1/templates", "root_path": "/api"}, "/v1/templates"),
        ({"path": "/api/health", "root_path": "/api"}, "/health"),
        ({"path": "/v1/templates", "root_path": "/api"}, "/v1/templates"),
        ({"path": "/api", "root_path": "/api"}, ""),
        ({"path": "/apiary/v1", "root_path": "/api"}, "/apiary/v1"),
    ],
)
def test_the_path_source_strips_exactly_what_the_router_strips(scope: dict[str, str], expected: str) -> None:
    """Inclui o caso em que o prefixo é só um prefixo textual (`/apiary` vs `/api`)."""
    assert middleware_api_key.get_route_path(scope) == expected  # type: ignore[arg-type]
