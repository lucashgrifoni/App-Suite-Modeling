"""
O 413 de `/v1/imports/*` no envelope documentado.

`docs/features/API.md` diz que as rotas de negócio devolvem `detail` como `{code, message}`, e
todos os erros vizinhos desta mesma rota cumprem-no (`IMPORT_EMPTY_ARTIFACT`, `IMPORT_NOT_UTF8`,
`IMPORT_ARTIFACT_INVALID`). O 413 devolvia uma string solta, por isso um cliente escrito contra
o contrato — incluindo o parser do próprio frontend, que lê `detail.code` — rebentava com
`TypeError: string indices must be integers` exatamente no erro que um utilizador provoca por
acidente ao arrastar o ficheiro errado.

A correção estava bloqueada por dois testes que fixavam a forma errada:
`tests/test_api.py` (`"2 MiB" in r.json()["detail"]`, verdade só enquanto `detail` for string) e
`tests/test_p2r2_api_contract_gaps.py` (`isinstance(r.json()["detail"], str)`, escrito de
propósito para registar o adiamento). Ambos foram atualizados junto com esta correção.
"""

from __future__ import annotations

import httpx
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402
from otm_api.routers.imports import _MAX_BYTES  # noqa: E402

_ROUTES = ["openapi", "terraform", "kubernetes"]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _oversized_upload(client: TestClient, route: str) -> httpx.Response:
    payload = b"x" * (_MAX_BYTES + 1)
    return client.post(f"/v1/imports/{route}", files={"file": ("big.yaml", payload, "application/yaml")})


@pytest.mark.parametrize("route", _ROUTES)
def test_the_oversize_error_uses_the_documented_envelope(client: TestClient, route: str) -> None:
    """O sintoma: `detail["code"]` levantava TypeError num cliente conforme."""
    assert isinstance(_oversized_upload(client, route).json()["detail"], dict)


@pytest.mark.parametrize("route", _ROUTES)
def test_the_oversize_error_carries_a_stable_code(client: TestClient, route: str) -> None:
    assert _oversized_upload(client, route).json()["detail"]["code"] == "IMPORT_TOO_LARGE"


@pytest.mark.parametrize("route", _ROUTES)
def test_the_oversize_error_is_still_a_413(client: TestClient, route: str) -> None:
    assert _oversized_upload(client, route).status_code == 413


def test_the_message_still_names_the_limit_the_caller_hit(client: TestClient) -> None:
    """Um código estável sem o número deixa o utilizador sem saber para que tamanho cortar."""
    assert "2 MiB" in _oversized_upload(client, "openapi").json()["detail"]["message"]


def test_the_message_is_written_for_a_person(client: TestClient) -> None:
    message = _oversized_upload(client, "openapi").json()["detail"]["message"]

    assert message.endswith(".")


def test_the_boundary_did_not_move(client: TestClient) -> None:
    """A correção era do envelope; exatamente no limite continua a passar."""
    exactly = b"paths: {}\n" + b"#" * (_MAX_BYTES - len(b"paths: {}\n"))

    r = client.post("/v1/imports/openapi", files={"file": ("edge.yaml", exactly, "application/yaml")})

    assert r.status_code != 413


def test_the_oversize_message_is_localised(client: TestClient) -> None:
    """Os erros vizinhos são traduzidos; um 413 só em inglês seria a nova divergência."""
    payload = b"x" * (_MAX_BYTES + 1)
    r = client.post(
        "/v1/imports/openapi",
        files={"file": ("big.yaml", payload, "application/yaml")},
        headers={"Accept-Language": "pt-BR"},
    )

    assert "limite" in r.json()["detail"]["message"]


def test_a_neighbouring_import_error_still_uses_the_same_envelope(client: TestClient) -> None:
    r = client.post("/v1/imports/openapi", files={"file": ("empty.yaml", b"", "application/yaml")})

    assert r.json()["detail"]["code"] == "IMPORT_EMPTY_ARTIFACT"
