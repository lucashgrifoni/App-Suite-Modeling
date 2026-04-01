"""Rotas HTTP — importação assistida de artefactos (rascunho canónico)."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from otm_artifact_import.types import ArtifactImportResult

from otm_api.schemas.bodies import ArtifactImportResponse, InferenceRecordBody
from otm_api.services.imports import (
    import_kubernetes_bytes,
    import_openapi_bytes,
    import_terraform_bytes,
)

router = APIRouter(prefix="/imports", tags=["Importação assistida"])

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


async def _read_limited(file: UploadFile) -> tuple[bytes, str]:
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Artefacto excede limite de 2 MiB (MVP).",
        )
    name = file.filename or "upload"
    return data, name


@router.post(
    "/openapi",
    summary="Rascunho a partir de OpenAPI/Swagger",
    description=(
        "Corpo: `multipart/form-data` com campo `file` (YAML/JSON). "
        "Devolve rascunho canónico e inferências."
    ),
)
async def import_openapi_route(file: UploadFile = File(...)) -> ArtifactImportResponse:
    try:
        data, name = await _read_limited(file)
        return _serialize(import_openapi_bytes(data, filename=name))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/terraform",
    summary="Rascunho a partir de Terraform (.tf)",
    description=(
        "Um único ficheiro `.tf` ou texto HCL agregado. "
        "Para pastas, prefira a CLI: `otm import terraform`."
    ),
)
async def import_terraform_route(file: UploadFile = File(...)) -> ArtifactImportResponse:
    try:
        data, name = await _read_limited(file)
        return _serialize(import_terraform_bytes(data, filename=name))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/kubernetes",
    summary="Rascunho a partir de manifests Kubernetes",
    description="YAML multi-documento (vários recursos separados por `---`).",
)
async def import_kubernetes_route(file: UploadFile = File(...)) -> ArtifactImportResponse:
    try:
        data, name = await _read_limited(file)
        return _serialize(import_kubernetes_bytes(data, filename=name))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
