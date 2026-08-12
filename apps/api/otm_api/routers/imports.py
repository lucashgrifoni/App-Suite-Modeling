"""HTTP routes — assisted artifact import (canonical draft)."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from otm_artifact_import.types import ArtifactImportResult

from otm_api.api_error_messages import msg_import_empty_artifact, msg_import_not_utf8
from otm_api.routers._errors import error_detail
from otm_api.schemas.bodies import ArtifactImportResponse, InferenceRecordBody
from otm_api.services.imports import (
    import_kubernetes_bytes,
    import_openapi_bytes,
    import_terraform_bytes,
)

router = APIRouter(prefix="/imports", tags=["Assisted import"])

_MAX_BYTES = 2 * 1024 * 1024


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


async def _read_limited(file: UploadFile) -> tuple[bytes, str]:
    # Bounded read: never materialize more than the limit (+1 sentinel byte) in process memory,
    # even if a client sends a much larger artifact. Receive-time / on-disk request-body caps for
    # internet-facing deployments are delegated to the gateway or ASGI server
    # (see docs/architecture/DEPLOYMENT_INVARIANTS.md).
    data = await file.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        # Divergência conhecida e documentada em `docs/features/API.md`: este `detail` é uma
        # string solta, enquanto todos os erros vizinhos desta rota (e o contrato) usam
        # `{code, message}` — um cliente que faça `detail["code"]` rebenta com `TypeError`.
        # A correção é trocar isto por `_import_error(..., code="IMPORT_TOO_LARGE", ...)`, e
        # está retida por um único teste que afirma `"2 MiB" in r.json()["detail"]`
        # (`tests/test_api.py`), verdade apenas enquanto `detail` for string. Ver
        # `tests/test_p2r2_api_contract_gaps.py`, que fixa o estado atual e falha assim que
        # esse teste for corrigido para `["detail"]["message"]`.
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Artifact exceeds 2 MiB limit (MVP).",
        )
    # Zero bytes é o único caso inequívoco: `terraform` e `kubernetes` devolviam 200 com um
    # rascunho canónico completo a partir de um ficheiro vazio, que seguia para validate/analyze
    # como se fosse um modelo. Conteúdo não reconhecido mas presente continua a produzir
    # rascunho + `unknowns[]`, que é o contrato deliberado do import assistido.
    if not data:
        raise _import_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="IMPORT_EMPTY_ARTIFACT",
            message=msg_import_empty_artifact(),
        )
    name = file.filename or "upload"
    return data, name


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
        # Mensagem do importador (ex.: "Raiz do artefacto deve ser um objecto (mapping)."):
        # é acionável e escrita para humanos; o que faltava era o envelope à volta dela.
        raise _import_error(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="IMPORT_ARTIFACT_INVALID",
            message=str(e),
        ) from e


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
