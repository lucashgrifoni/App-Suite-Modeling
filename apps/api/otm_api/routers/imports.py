"""HTTP routes — assisted artifact import (canonical draft)."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from otm_artifact_import.types import ArtifactImportResult

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


async def _read_limited(file: UploadFile) -> tuple[bytes, str]:
    data = await file.read()
    if len(data) > _MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Artifact exceeds 2 MiB limit (MVP).",
        )
    name = file.filename or "upload"
    return data, name


@router.post(
    "/openapi",
    summary="Draft from OpenAPI/Swagger",
    description=("Body: `multipart/form-data` with field `file` (YAML/JSON). Returns canonical draft and inferences."),
    response_model=ArtifactImportResponse,
)
async def import_openapi_route(file: UploadFile = File(...)) -> ArtifactImportResponse:
    try:
        data, name = await _read_limited(file)
        return _serialize(import_openapi_bytes(data, filename=name))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/terraform",
    summary="Draft from Terraform (.tf)",
    description=(
        "A single `.tf` file or aggregated HCL text. For directories, prefer the CLI: `otm import terraform`."
    ),
    response_model=ArtifactImportResponse,
)
async def import_terraform_route(file: UploadFile = File(...)) -> ArtifactImportResponse:
    try:
        data, name = await _read_limited(file)
        return _serialize(import_terraform_bytes(data, filename=name))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post(
    "/kubernetes",
    summary="Draft from Kubernetes manifests",
    description="Multi-document YAML (multiple resources separated by `---`).",
    response_model=ArtifactImportResponse,
)
async def import_kubernetes_route(file: UploadFile = File(...)) -> ArtifactImportResponse:
    try:
        data, name = await _read_limited(file)
        return _serialize(import_kubernetes_bytes(data, filename=name))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
