"""
Três buracos de contrato na API, todos do mesmo tipo: o produto documenta uma coisa e a rota
faz outra, sem o dizer.

- Em `staging`/`production` a lista de cabeçalhos CORS não incluía `X-OTM-API-Key`, ou seja, o
  preflight de qualquer cliente de browser era rejeitado com 400 exatamente para o mecanismo de
  autenticação que a própria API documenta e que o corpo do 401 manda usar. Em `development`,
  `allow_headers=["*"]` escondia-o.
- `group_by` em `/v1/remediation/backlog` aceitava qualquer string e caía em silêncio no
  agrupamento por defeito — `root_cause`, `severity`, `totally-bogus` devolviam 200 com um corpo
  byte-a-byte igual ao default. O parâmetro vizinho `format` já era estrito.
- O 413 do upload demasiado grande devolvia `detail` como string solta, fora do envelope
  `{code, message}` que todos os outros erros da mesma rota seguem. Corrigido depois, em
  conjunto com o teste de `tests/test_api.py` que o segurava.
"""

from __future__ import annotations

import hashlib
import importlib
import os
from collections.abc import Iterator
from typing import Any

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.cors_settings import resolve_cors_profile  # noqa: E402
from otm_api.main import app  # noqa: E402

_ORIGIN = "https://app.example.com"
_ENVS = ["OTM_ENV", "OTM_CORS_ORIGINS", "OTM_API_KEY", "OTM_RATE_LIMIT", "OTM_RATE_LIMIT_DISABLED"]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# --- CORS: o cabeçalho de autenticação da própria API ----------------------------------


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_the_api_key_header_is_allowed_by_cors(environment: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_ENV", environment)

    assert "X-OTM-API-Key" in resolve_cors_profile().allow_headers


@pytest.fixture
def deployed_app() -> Iterator[Any]:
    """A app recarregada com o perímetro que um deployment real usa."""
    os.environ["OTM_ENV"] = "production"
    os.environ["OTM_CORS_ORIGINS"] = _ORIGIN
    os.environ["OTM_API_KEY"] = "s3cr3t-Key-abc123"
    os.environ["OTM_RATE_LIMIT_DISABLED"] = "1"
    import otm_api.main as main

    importlib.reload(main)
    yield main.app
    for name in _ENVS:
        os.environ.pop(name, None)
    importlib.reload(main)


def _preflight(client: TestClient, requested: str) -> Any:
    return client.options(
        "/v1/models/validate",
        headers={
            "Origin": _ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": requested,
        },
    )


def test_a_browser_preflight_asking_for_the_key_header_is_accepted(deployed_app: Any) -> None:
    """O sintoma: 400 "Disallowed CORS headers", e o browser nunca chega a fazer o pedido."""
    r = _preflight(TestClient(deployed_app), "content-type, x-otm-api-key")

    assert r.status_code == 200, r.text


def test_the_preflight_echoes_the_key_header_back(deployed_app: Any) -> None:
    r = _preflight(TestClient(deployed_app), "content-type, x-otm-api-key")

    assert "x-otm-api-key" in r.headers["access-control-allow-headers"].lower()


def test_the_other_documented_auth_header_still_passes_preflight(deployed_app: Any) -> None:
    r = _preflight(TestClient(deployed_app), "content-type, authorization")

    assert r.status_code == 200, r.text


def test_an_undeclared_header_is_still_refused(deployed_app: Any) -> None:
    """Alargar a lista não pode virar `*` por acidente."""
    r = _preflight(TestClient(deployed_app), "content-type, x-anything-goes")

    assert r.status_code == 400


def test_the_key_header_still_authenticates_a_non_browser_client(deployed_app: Any) -> None:
    client = TestClient(deployed_app)

    r = client.get("/v1/templates", headers={"X-OTM-API-Key": "s3cr3t-Key-abc123"})

    assert r.status_code == 200, r.text


# --- group_by ---------------------------------------------------------------------------


@pytest.fixture
def analysed(client: TestClient) -> dict[str, Any]:
    doc = client.post("/v1/templates/admin-portal/instantiate").json()["document"]
    return {"document": doc, "analysis": client.post("/v1/models/analyze", json={"document": doc}).json()}


def _backlog(client: TestClient, body: dict[str, Any], query: str) -> Any:
    return client.post(f"/v1/remediation/backlog?format=markdown{query}", json=body)


@pytest.mark.parametrize("value", ["root_cause", "severity", "totally-bogus", "ROOT-CAUSE", ""])
def test_an_unrecognised_grouping_is_rejected(client: TestClient, analysed: dict[str, Any], value: str) -> None:
    """O sintoma: 200 com o agrupamento por defeito e nada a dizer que o pedido foi ignorado."""
    r = _backlog(client, analysed, f"&group_by={value}")

    assert r.status_code == 422, r.text


def test_the_rejection_carries_a_stable_code(client: TestClient, analysed: dict[str, Any]) -> None:
    r = _backlog(client, analysed, "&group_by=totally-bogus")

    assert r.json()["detail"]["code"] == "REMEDIATION_GROUP_BY_INVALID"


def test_the_rejection_lists_the_accepted_values(client: TestClient, analysed: dict[str, Any]) -> None:
    """Sem os valores aceites, o utilizador fica a saber que errou mas não o que escrever."""
    message = _backlog(client, analysed, "&group_by=root_cause").json()["detail"]["message"]

    assert "root-cause, control, category" in message


def test_an_unrecognised_grouping_is_rejected_for_json_too(client: TestClient, analysed: dict[str, Any]) -> None:
    """O valor é inválido independentemente do formato; aceitá-lo em json é a mesma mentira."""
    r = client.post("/v1/remediation/backlog?format=json&group_by=totally-bogus", json=analysed)

    assert r.status_code == 422, r.text


@pytest.mark.parametrize("value", ["root-cause", "control", "category"])
def test_every_documented_grouping_is_accepted(client: TestClient, analysed: dict[str, Any], value: str) -> None:
    r = _backlog(client, analysed, f"&group_by={value}")

    assert r.status_code == 200, r.text


def test_omitting_the_grouping_still_works(client: TestClient, analysed: dict[str, Any]) -> None:
    r = _backlog(client, analysed, "")

    assert r.status_code == 200, r.text


def test_the_documented_groupings_really_change_the_report(client: TestClient, analysed: dict[str, Any]) -> None:
    """A validação não pode passar a rejeitar valores que produzem relatórios distintos."""
    digests = {
        value: hashlib.sha256(_backlog(client, analysed, f"&group_by={value}").content).hexdigest()
        for value in ("root-cause", "control", "category")
    }

    assert len(set(digests.values())) == 3


# --- 413 no envelope documentado --------------------------------------------------------


def _oversized() -> bytes:
    return b"openapi: 3.0.0\ninfo:\n  title: Big\n  version: '1'\npaths: {}\n" + b"#" * (2 * 1024 * 1024)


def test_an_oversized_upload_is_still_refused(client: TestClient) -> None:
    r = client.post("/v1/imports/openapi", files={"file": ("big.yaml", _oversized(), "application/yaml")})

    assert r.status_code == 413


def test_the_oversize_error_is_inside_the_documented_envelope(client: TestClient) -> None:
    """A correção adiada, agora aplicada.

    Este teste fixava o estado errado de propósito (`isinstance(detail, str)`) porque a correção
    estava retida por `tests/test_api.py`, que afirmava `"2 MiB" in r.json()["detail"]` — só
    verdade enquanto `detail` fosse string — e pertencia a outro âmbito. Os dois ficheiros
    mudaram juntos: `detail` é agora o envelope `{code, message}` documentado em
    `docs/features/API.md`, como todos os outros erros desta rota. Ver
    `tests/test_p2r3_api_import_413_envelope.py`.
    """
    r = client.post("/v1/imports/openapi", files={"file": ("big.yaml", _oversized(), "application/yaml")})

    assert r.json()["detail"]["code"] == "IMPORT_TOO_LARGE"


def test_the_size_boundary_did_not_move(client: TestClient) -> None:
    """Exatamente no limite continua a passar; o defeito era o envelope, não a fronteira."""
    exactly = b"paths: {}\n" + b"#" * (2 * 1024 * 1024 - len(b"paths: {}\n"))

    r = client.post("/v1/imports/openapi", files={"file": ("edge.yaml", exactly, "application/yaml")})

    assert r.status_code != 413


def test_a_neighbouring_import_error_keeps_its_envelope(client: TestClient) -> None:
    r = client.post("/v1/imports/openapi", files={"file": ("empty.yaml", b"", "application/yaml")})

    assert r.json()["detail"]["code"] == "IMPORT_EMPTY_ARTIFACT"
