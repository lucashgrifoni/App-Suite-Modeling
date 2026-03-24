from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from otm_threat_engine import AnalysisResult
from pydantic import ValidationError as PydanticValidationError

from otm_api.schemas.bodies import ExportBody, ExportResponse
from otm_api.services.documents import document_from_payload
from otm_api.services.exports import build_exports

router = APIRouter(prefix="/exports", tags=["Exportação"])


@router.post(
    "",
    response_model=ExportResponse,
    summary="Exportar resultados",
    description=(
        "Gera um ou mais artefactos (JSON, Markdown, Mermaid, bundle). "
        "Se pedir formatos que dependem de análise e não enviar `analysis`, o motor corre automaticamente."
    ),
)
def export_artifacts(body: ExportBody) -> ExportResponse:
    try:
        doc = document_from_payload(body.document)
    except PydanticValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "DOCUMENT_VALIDATION_ERROR",
                "message": "O documento não cumpre o schema canónico.",
                "errors": e.errors(),
            },
        ) from e

    analysis: AnalysisResult | None = None
    if body.analysis is not None:
        try:
            analysis = AnalysisResult.model_validate(body.analysis)
        except PydanticValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "ANALYSIS_VALIDATION_ERROR",
                    "message": "O campo analysis não é um AnalysisResult válido.",
                    "errors": e.errors(),
                },
            ) from e

    try:
        artifacts = build_exports(
            doc,
            formats=body.formats,
            analysis=analysis,
            pack_id=body.pack_id,
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PACK_NOT_FOUND", "message": str(e)},
        ) from e

    return ExportResponse(artifacts=artifacts)
