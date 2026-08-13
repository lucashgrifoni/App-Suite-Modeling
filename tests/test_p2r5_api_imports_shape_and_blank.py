"""
Regressão: `/v1/imports/*` e as duas formas de artefacto que escapavam ao envelope documentado.

1. **Forma inesperada = 500.** Um artefacto que faz *parse* mas cujos nós não têm o tipo
   previsto — `{"openapi":"3.0.0","info":[1]}`, `info` como lista — atravessava o importador
   até um acesso duck-typed (`(data.get("info") or {}).get("title")`) e saía como
   `500 INTERNAL_ERROR`. Pelo menos 15 formas, todas alcançáveis com um upload simples, na
   rota cuja função é precisamente ingerir artefactos de terceiros. `docs/features/API.md`
   documenta `IMPORT_ARTIFACT_INVALID`/400 para "o artefacto é texto mas não tem a forma
   esperada" e diz que "não há exceções ao envelope nestas rotas".

2. **Ficheiro em branco = 200 + rascunho canónico.** `IMPORT_EMPTY_ARTIFACT` testava
   `not data`, ou seja *literalmente* zero bytes. Um ficheiro com uma newline, um espaço, um
   CRLF ou só um BOM — o que o git, o "guardar" de um editor sobre um ficheiro vazio e uma
   exportação com BOM produzem — devolvia 200 com um rascunho completo que passava em
   `/v1/models/validate` e `/v1/models/analyze` como se fosse um modelo. As três rotas
   discordavam ainda entre si sobre o mesmo ficheiro em branco.

O que **não** muda: conteúdo presente mas não reconhecido (um comentário, HTML, um scalar)
continua a produzir rascunho + `unknowns[]`, que é o contrato deliberado do import assistido.
"""

from __future__ import annotations

import logging

import httpx
import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402

_ROUTES = ["openapi", "terraform", "kubernetes"]

#: Artefactos que fazem parse mas cujos nós não têm o tipo que o importador assume.
_MALFORMED_SHAPES = [
    b'{"openapi":"3.0.0","info":[1]}',
    b'{"openapi":"3.0.0","info":"x"}',
    b'{"openapi":"3.0.0","info":5}',
    b'{"openapi":"3.0.0","info":true}',
    b'{"openapi":"3.0.0","info":[{"title":"t"}]}',
    b'{"openapi":"3.0.0","servers":5}',
    b'{"openapi":"3.0.0","servers":true}',
    b'{"swagger":"2.0","info":[1]}',
    b'{"swagger":"2.0","info":"x"}',
    b'{"swagger":"2.0","info":5}',
    b'{"swagger":"2.0","host":[1]}',
    b'{"swagger":"2.0","host":5}',
    b'{"swagger":"2.0","host":true}',
    b'{"swagger":"2.0","basePath":[1]}',
    b'{"swagger":"2.0","basePath":7}',
    b'{"swagger":"2.0","basePath":true}',
    b"openapi: 3.0.0\ninfo:\n  - a\n",
]

#: Uploads sem artefacto nenhum. Só o primeiro era recusado.
_BLANK = [b"", b"\n", b" ", b"\r\n", b"\t", b"   \n\t  \n", b"\xef\xbb\xbf", b"\xef\xbb\xbf\r\n"]

#: Conteúdo presente que o importador não reconhece: contrato do import assistido, não erro.
_UNRECOGNISED = [b"# nothing here\n", b"  # comentario  ", b"resource_but_not_really\n"]


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _upload(client: TestClient, route: str, data: bytes, name: str = "artifact.yaml") -> httpx.Response:
    return client.post(f"/v1/imports/{route}", files={"file": (name, data, "application/octet-stream")})


# --- 1. forma inesperada: 400 documentado, não 500 ------------------------------------


@pytest.mark.parametrize("payload", _MALFORMED_SHAPES)
def test_a_malformed_but_parseable_artifact_is_not_a_server_error(client: TestClient, payload: bytes) -> None:
    assert _upload(client, "openapi", payload).status_code == 400


@pytest.mark.parametrize("payload", _MALFORMED_SHAPES)
def test_a_malformed_but_parseable_artifact_carries_the_documented_code(client: TestClient, payload: bytes) -> None:
    assert _upload(client, "openapi", payload).json()["detail"]["code"] == "IMPORT_ARTIFACT_INVALID"


def test_the_refusal_keeps_the_documented_envelope(client: TestClient) -> None:
    """O sintoma no cliente: `detail["code"]` levantava `TypeError` porque `detail` não existia."""
    body = _upload(client, "openapi", b'{"openapi":"3.0.0","info":[1]}').json()

    assert isinstance(body.get("detail"), dict)


def test_the_refusal_does_not_leak_the_internal_exception(client: TestClient) -> None:
    message = _upload(client, "openapi", b'{"openapi":"3.0.0","info":[1]}').json()["detail"]["message"]

    assert "AttributeError" not in message and "object has no attribute" not in message


def test_the_refusal_is_actionable(client: TestClient) -> None:
    message = _upload(client, "openapi", b'{"openapi":"3.0.0","info":[1]}').json()["detail"]["message"]

    assert message.strip()


def test_the_rejected_shape_is_still_recorded_in_the_structured_log(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Converter o 500 em 400 não pode apagar o rasto de um defeito real do importador."""
    with caplog.at_level(logging.ERROR, logger="otm.api"):
        _upload(client, "openapi", b'{"openapi":"3.0.0","info":[1]}')

    assert "import_artifact_shape_rejected" in caplog.text


def test_the_logged_record_keeps_the_original_exception(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.ERROR, logger="otm.api"):
        _upload(client, "openapi", b'{"openapi":"3.0.0","info":[1]}')

    assert "AttributeError" in caplog.text


# --- 2. ficheiro em branco: as três rotas concordam -----------------------------------


@pytest.mark.parametrize("route", _ROUTES)
@pytest.mark.parametrize("payload", _BLANK)
def test_a_blank_upload_is_refused(client: TestClient, route: str, payload: bytes) -> None:
    assert _upload(client, route, payload, name="blank.tf").status_code == 400


@pytest.mark.parametrize("route", _ROUTES)
@pytest.mark.parametrize("payload", _BLANK)
def test_every_route_names_the_same_reason_for_a_blank_upload(client: TestClient, route: str, payload: bytes) -> None:
    """As três discordavam: 200, `IMPORT_ARTIFACT_INVALID` e `IMPORT_EMPTY_ARTIFACT` para o mesmo ficheiro."""
    detail = _upload(client, route, payload, name="blank.tf").json()["detail"]

    assert detail["code"] == "IMPORT_EMPTY_ARTIFACT"


@pytest.mark.parametrize("route", _ROUTES)
@pytest.mark.parametrize("payload", _BLANK)
def test_a_blank_upload_never_yields_a_draft_document(client: TestClient, route: str, payload: bytes) -> None:
    """O dano real: o rascunho seguia para validate/analyze como se fosse um modelo."""
    assert "document" not in _upload(client, route, payload, name="blank.tf").json()


# --- o que não pode partir: conteúdo presente continua a dar rascunho -----------------


@pytest.mark.parametrize("route", ["terraform", "kubernetes"])
@pytest.mark.parametrize("payload", _UNRECOGNISED)
def test_present_but_unrecognised_content_is_still_a_draft(client: TestClient, route: str, payload: bytes) -> None:
    """A fronteira fica no conteúdo, não no reconhecimento — senão o import assistido morria."""
    assert _upload(client, route, payload, name="main.tf").status_code == 200


@pytest.mark.parametrize("route", ["terraform", "kubernetes"])
@pytest.mark.parametrize("payload", _UNRECOGNISED)
def test_the_unrecognised_draft_still_declares_its_unknowns(client: TestClient, route: str, payload: bytes) -> None:
    assert _upload(client, route, payload, name="main.tf").json()["unknowns"]


def test_a_real_openapi_artifact_still_imports(client: TestClient) -> None:
    """Controlo directo do risco oposto: apertar a forma não pode recusar um artefacto válido."""
    spec = b'{"openapi":"3.0.0","info":{"title":"Orders API"},"paths":{"/orders":{"get":{}}}}'

    assert _upload(client, "openapi", spec).status_code == 200


def test_a_real_openapi_artifact_keeps_its_title(client: TestClient) -> None:
    spec = b'{"openapi":"3.0.0","info":{"title":"Orders API"},"paths":{"/orders":{"get":{}}}}'

    assert "Orders API" in _upload(client, "openapi", spec).json()["document"]["metadata"]["title"]


def test_an_openapi_artifact_with_a_falsy_info_still_imports(client: TestClient) -> None:
    """`info: {}` e `servers: []` sempre foram aceites pelo guarda `x or default`; continuam."""
    spec = b'{"openapi":"3.0.0","info":{},"servers":[],"paths":{"/x":{"get":{}}}}'

    assert _upload(client, "openapi", spec).status_code == 200


def test_a_real_terraform_artifact_still_imports(client: TestClient) -> None:
    tf = b'resource "aws_s3_bucket" "logs" {\n  bucket = "logs"\n}\n'

    assert _upload(client, "terraform", tf, name="main.tf").status_code == 200


def test_a_real_kubernetes_manifest_still_imports(client: TestClient) -> None:
    manifest = b"apiVersion: v1\nkind: Service\nmetadata:\n  name: api\n"

    assert _upload(client, "kubernetes", manifest, name="svc.yaml").status_code == 200


def test_a_non_utf8_artifact_still_answers_not_utf8(client: TestClient) -> None:
    """O teste da forma é feito sobre bytes para não roubar este caso ao seu próprio código."""
    detail = _upload(client, "kubernetes", "nome: sessão".encode("latin-1")).json()["detail"]

    assert detail["code"] == "IMPORT_NOT_UTF8"


def test_an_unparseable_artifact_still_keeps_the_parser_location(client: TestClient) -> None:
    """O `ValueError` com causa YAML mantém o caminho próprio, com "line N" na mensagem."""
    detail = _upload(client, "kubernetes", b"a: [\n").json()["detail"]

    assert "line" in detail["message"]
