"""
Regressão: os erros de `/v1/imports/*` têm de respeitar o envelope documentado.

`docs/features/API.md` (secção "Erros") diz que as rotas de negócio devolvem `detail` com
um objeto `{code, message}`, e o resto da API cumpre-o (`PACK_NOT_FOUND`,
`REMEDIATION_INPUT`). As rotas de import devolviam uma string solta — e, no caminho de
falha mais comum, essa string era o texto cru da excepção do codec Python
(`'utf-8' codec can't decode byte 0xff in position 3...`). Um cliente escrito contra o
contrato rebentava com `TypeError: string indices must be integers`.

Além disso, um upload de zero bytes: `/v1/imports/openapi` recusava-o, `terraform` e
`kubernetes` devolviam 200 com um rascunho canónico "vazio" pronto a analisar.
"""

from __future__ import annotations

import httpx
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402

_ROUTES = ["openapi", "terraform", "kubernetes"]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _upload(client: TestClient, route: str, data: bytes, name: str = "artifact.yaml") -> httpx.Response:
    return client.post(f"/v1/imports/{route}", files={"file": (name, data, "application/octet-stream")})


# --- artefacto vazio ------------------------------------------------------------------


@pytest.mark.parametrize("route", _ROUTES)
def test_empty_upload_is_rejected(client: TestClient, route: str) -> None:
    assert _upload(client, route, b"").status_code == 400


@pytest.mark.parametrize("route", _ROUTES)
def test_empty_upload_carries_a_stable_code(client: TestClient, route: str) -> None:
    assert _upload(client, route, b"").json()["detail"]["code"] == "IMPORT_EMPTY_ARTIFACT"


@pytest.mark.parametrize("route", _ROUTES)
def test_empty_upload_never_yields_a_draft_document(client: TestClient, route: str) -> None:
    assert "document" not in _upload(client, route, b"").json()


def test_non_empty_but_unrecognised_terraform_is_still_a_draft(client: TestClient) -> None:
    """O import assistido é semi-automático por desenho: só o ficheiro vazio é inequívoco."""
    r = _upload(client, "terraform", b"   ", name="main.tf")
    assert r.status_code == 200, r.text


def test_the_unrecognised_draft_says_nothing_was_found(client: TestClient) -> None:
    r = _upload(client, "terraform", b"   ", name="main.tf")
    assert r.json()["unknowns"]


# --- envelope de erro -----------------------------------------------------------------


def test_undecodable_artifact_is_a_structured_error(client: TestClient) -> None:
    detail = _upload(client, "kubernetes", "nome: sessão".encode("latin-1")).json()["detail"]
    assert detail["code"] == "IMPORT_NOT_UTF8"


def test_undecodable_artifact_does_not_leak_the_codec_exception(client: TestClient) -> None:
    detail = _upload(client, "openapi", b"\x00\x01\x02\xff\xfe\xfd", name="garbage.bin").json()["detail"]
    assert "codec can't decode" not in detail["message"]


def test_undecodable_artifact_message_is_actionable(client: TestClient) -> None:
    detail = _upload(client, "openapi", b"\x00\x01\x02\xff\xfe\xfd", name="garbage.bin").json()["detail"]
    assert "UTF-8" in detail["message"]


def test_malformed_artifact_is_a_structured_error(client: TestClient) -> None:
    detail = _upload(client, "openapi", b"<html><body>not a spec</body></html>", name="page.html").json()["detail"]
    assert detail["code"] == "IMPORT_ARTIFACT_INVALID"


def test_malformed_artifact_keeps_the_parser_explanation(client: TestClient) -> None:
    """A mensagem do importador é acionável; o que faltava era o envelope à volta dela."""
    detail = _upload(client, "openapi", b"<html><body>not a spec</body></html>", name="page.html").json()["detail"]
    assert detail["message"]


@pytest.mark.parametrize("route", _ROUTES)
def test_every_import_error_detail_is_an_object(client: TestClient, route: str) -> None:
    """O sintoma original: `body["detail"]["code"]` levantava TypeError."""
    detail = _upload(client, route, b"").json()["detail"]
    assert isinstance(detail, dict)


# --- caminho feliz intacto ------------------------------------------------------------


def test_a_valid_openapi_spec_still_imports(client: TestClient) -> None:
    spec = b'{"openapi": "3.0.0", "info": {"title": "T", "version": "1"}, "paths": {}}'
    r = _upload(client, "openapi", spec, name="api.json")
    assert r.status_code == 200, r.text


def test_a_valid_terraform_file_still_imports(client: TestClient) -> None:
    tf = b'resource "aws_s3_bucket" "b" { bucket = "x" }\n'
    r = _upload(client, "terraform", tf, name="main.tf")
    assert r.status_code == 200, r.text


def test_a_valid_manifest_still_imports(client: TestClient) -> None:
    k8s = b"apiVersion: v1\nkind: Service\nmetadata: {name: api}\nspec: {ports: [{port: 80}]}\n"
    r = _upload(client, "kubernetes", k8s, name="k8s.yaml")
    assert r.status_code == 200, r.text
