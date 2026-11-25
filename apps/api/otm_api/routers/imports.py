"""HTTP routes — assisted artifact import (canonical draft)."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable

import yaml
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from otm_artifact_import.types import ArtifactImportResult

from otm_api.api_error_messages import (
    msg_import_artifact_invalid,
    msg_import_empty_artifact,
    msg_import_not_utf8,
    msg_import_too_large,
)
from otm_api.error_models import API_ERROR_RESPONSES
from otm_api.routers._errors import error_detail
from otm_api.schemas.bodies import ArtifactImportResponse, InferenceRecordBody
from otm_api.services.imports import (
    import_kubernetes_bytes,
    import_openapi_bytes,
    import_terraform_bytes,
)

router = APIRouter(prefix="/imports", tags=["Assisted import"], responses=API_ERROR_RESPONSES)

LOG = logging.getLogger("otm.api")

_MAX_MIB = 2
_MAX_BYTES = _MAX_MIB * 1024 * 1024

# Um BOM UTF-8 não é espaço em branco para o `bytes.strip()`, mas é exatamente o que um editor
# do Windows grava num ficheiro "vazio" — por isso conta como ausência de conteúdo tal como
# `\n` ou `\r\n`. Ver `_has_no_content`.
_UTF8_BOM = b"\xef\xbb\xbf"


def _serialize(result: ArtifactImportResult) -> ArtifactImportResponse:
    return ArtifactImportResponse(
        document=result.document.model_dump(mode="json", by_alias=True),
        inferences=[
            InferenceRecordBody(
                id=i.id,
                message=i.message,
                confidence=i.confidence,
                source=i.source,
                related_component_ids=i.related_component_ids,
            )
            for i in result.inferences
        ],
        unknowns=result.unknowns,
        assumptions=result.assumptions,
        explanations=list(result.explanations),
    )


def _import_error(*, status_code: int, code: str, message: str) -> HTTPException:
    """
    Erro de import no envelope documentado (`detail` = `{code, message}`).

    Estas rotas devolviam uma string solta em `detail`, ao contrário do resto da API
    (`PACK_NOT_FOUND`, `REMEDIATION_INPUT`, …), pelo que um cliente escrito contra o
    contrato de `docs/features/API.md` rebentava a ler `detail["code"]`.
    """
    return HTTPException(status_code=status_code, detail=error_detail(code=code, message=message))


def _parser_detail(exc: ValueError) -> str | None:
    """
    A explicação do parser YAML/JSON, quando existe uma.

    Sinal estrutural e não textual: `otm_artifact_import` encadeia o erro original
    (`raise ValueError(...) from e`) exatamente quando o conteúdo não se conseguiu ler, e
    encadeia outra coisa nenhuma. Depender disso, em vez de reconhecer a frase do pacote,
    é o que impede a tradução de deixar silenciosamente de funcionar quando essa frase mudar.
    """
    cause = exc.__cause__
    if isinstance(cause, (yaml.YAMLError, json.JSONDecodeError)):
        return str(cause)
    return None


def _has_no_content(data: bytes) -> bool:
    """O upload não traz artefacto nenhum: zero bytes, só espaço em branco, ou só um BOM.

    Testar `not data` deixava passar tudo o que não fosse *literalmente* zero bytes, e as três
    rotas discordavam entre si sobre o mesmo ficheiro em branco: `terraform` devolvia 200 com um
    rascunho canónico completo para `\\n`, ` `, `\\r\\n` e para um BOM sozinho; `kubernetes`
    recusava `   \\n\\t  \\n` (erro de tabulação do YAML) mas aceitava `\\n`; `openapi` recusava
    tudo. Um ficheiro com uma newline é o que o git, o "guardar" de qualquer editor sobre um
    ficheiro vazio e uma exportação só com BOM produzem — é o mesmo engano do utilizador, com a
    mesma consequência (um rascunho que passa em validate/analyze como se fosse um modelo).

    A fronteira fica no *conteúdo*, não no reconhecimento: um ficheiro só com um comentário tem
    conteúdo e continua a produzir rascunho + `unknowns[]`.

    Sobre bytes e não sobre texto descodificado, porque um artefacto que não é UTF-8 tem de
    continuar a responder `IMPORT_NOT_UTF8` e não este erro.
    """
    body = data[len(_UTF8_BOM) :] if data.startswith(_UTF8_BOM) else data
    return not body.strip()


async def _read_limited(file: UploadFile) -> tuple[bytes, str]:
    # Bounded read: never materialize more than the limit (+1 sentinel byte) in process memory,
    # even if a client sends a much larger artifact. Receive-time / on-disk request-body caps for
    # internet-facing deployments are delegated to the gateway or ASGI server
    # (see docs/architecture/DEPLOYMENT_INVARIANTS.md).
    data = await file.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        # Este era o único erro da rota fora do envelope `{code, message}`: `detail` saía como
        # string solta, e um cliente escrito contra `docs/features/API.md` — incluindo o parser
        # do frontend, que lê `detail.code` — rebentava com `TypeError` exatamente no erro que
        # um utilizador provoca por acidente ao arrastar o ficheiro errado.
        raise _import_error(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            code="IMPORT_TOO_LARGE",
            message=msg_import_too_large(limit_mib=_MAX_MIB),
        )
    # Um ficheiro sem conteúdo é o caso inequívoco: `terraform` e `kubernetes` devolviam 200 com
    # um rascunho canónico completo a partir dele, que seguia para validate/analyze como se
    # fosse um modelo. Conteúdo não reconhecido mas **presente** (um comentário, HTML, um
    # scalar) continua a produzir rascunho + `unknowns[]`, que é o contrato deliberado do
    # import assistido. Ver `_has_no_content` para onde passa a fronteira.
    if _has_no_content(data):
        raise _import_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="IMPORT_EMPTY_ARTIFACT",
            message=msg_import_empty_artifact(),
        )
    name = file.filename or "upload"
    return data, name


def _shape_error(exc: AttributeError | TypeError) -> HTTPException:
    """400 `IMPORT_ARTIFACT_INVALID` para um artefacto que se lê mas não tem a forma esperada.

    Estas rotas ingerem ficheiros de terceiros, e um artefacto **sintaticamente válido** cujos
    nós não têm o tipo previsto (`{"openapi":"3.0.0","info":[1]}` — `info` é uma lista, não um
    mapping) atravessava o importador até um acesso de atributo por duck typing
    (`(data.get("info") or {}).get("title")`, `data.get("host").strip()`) e saía como 500
    `INTERNAL_ERROR`. Pelo menos 15 formas distintas, todas alcançáveis com um upload simples,
    e `docs/features/API.md` diz que "não há exceções ao envelope nestas rotas".

    O facto é o mesmo que o `ValueError` já traduz — "o artefacto é texto mas não tem a forma
    esperada" — logo a resposta é a mesma. `AttributeError`/`TypeError` e mais nada: são as
    falhas que o acesso duck-typed a uma estrutura inesperada produz; qualquer outra excepção
    continua a subir para o handler genérico e a ser um 500.

    A conversão não apaga o rasto: um defeito real do importador que se manifeste assim
    deixaria de aparecer como 500 no log, por isso a excepção é registada aqui, com o
    `traceback` completo, sob um nome de evento próprio.
    """
    LOG.exception(
        "import_artifact_shape_rejected",
        extra={"event_name": "import_artifact_shape_rejected", "exc_type": type(exc).__name__},
    )
    return _import_error(
        status_code=status.HTTP_400_BAD_REQUEST,
        code="IMPORT_ARTIFACT_INVALID",
        message=msg_import_artifact_invalid(parser_detail=None),
    )


async def _draft_from_upload(
    file: UploadFile,
    importer: Callable[..., ArtifactImportResult],
) -> ArtifactImportResponse:
    data, name = await _read_limited(file)
    try:
        return _serialize(importer(data, filename=name))
    except UnicodeDecodeError as e:
        # `UnicodeDecodeError` é subclasse de `ValueError`: tem de vir primeiro, senão o texto
        # cru do codec (`byte 0xff in position 3`) volta a sair como mensagem user-facing.
        raise _import_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="IMPORT_NOT_UTF8",
            message=msg_import_not_utf8(),
        ) from e
    except ValueError as e:
        # A mensagem do importador é acionável mas está escrita em português fixo, e saía
        # tal e qual dentro de respostas em inglês (`Accept-Language: en`), ao lado de
        # irmãs traduzidas. A API reescreve-a no locale do pedido e preserva a parte que
        # não sabe produzir sozinha — a localização do parser ("line 3, column 5").
        raise _import_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="IMPORT_ARTIFACT_INVALID",
            message=msg_import_artifact_invalid(parser_detail=_parser_detail(e)),
        ) from e
    except (AttributeError, TypeError) as e:
        raise _shape_error(e) from e


@router.post(
    "/openapi",
    summary="Draft from OpenAPI/Swagger",
    description=("Body: `multipart/form-data` with field `file` (YAML/JSON). Returns canonical draft and inferences."),
)
async def import_openapi_route(file: UploadFile = File(...)) -> ArtifactImportResponse:
    return await _draft_from_upload(file, import_openapi_bytes)


@router.post(
    "/terraform",
    summary="Draft from Terraform (.tf)",
    description=(
        "A single `.tf` file or aggregated HCL text. For directories, prefer the CLI: `otm import terraform`."
    ),
)
async def import_terraform_route(file: UploadFile = File(...)) -> ArtifactImportResponse:
    return await _draft_from_upload(file, import_terraform_bytes)


@router.post(
    "/kubernetes",
    summary="Draft from Kubernetes manifests",
    description="Multi-document YAML (multiple resources separated by `---`).",
)
async def import_kubernetes_route(file: UploadFile = File(...)) -> ArtifactImportResponse:
    return await _draft_from_upload(file, import_kubernetes_bytes)
