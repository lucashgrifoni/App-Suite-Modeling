from __future__ import annotations

from fastapi import APIRouter
from otm_threat_engine import AnalysisResult
from pydantic import ValidationError as PydanticValidationError

from otm_api.routers._errors import (
    document_from_payload_or_422,
    raise_analysis_validation_error,
    raise_pack_not_found,
)
from otm_api.schemas.bodies import ExportBody, ExportResponse
from otm_api.services.exports import build_exports

router = APIRouter(prefix="/exports", tags=["Export"])


@router.post(
    "",
    summary="Export artifacts",
    description=(
        "Produces one or more artifacts (JSON, Markdown, Mermaid, bundle). "
        "If a format requires analysis and `analysis` is omitted, the engine runs automatically."
    ),
)
def export_artifacts(body: ExportBody) -> ExportResponse:
    doc = document_from_payload_or_422(body.document)

    analysis: AnalysisResult | None = None
    if body.analysis is not None:
        try:
            analysis = AnalysisResult.model_validate(body.analysis)
        except PydanticValidationError as e:
            raise raise_analysis_validation_error(e) from e

    try:
        artifacts = build_exports(
            doc,
            formats=body.formats,
            analysis=analysis,
            pack_id=body.pack_id,
        )
    except FileNotFoundError as e:
        raise raise_pack_not_found(e) from e

    return ExportResponse(artifacts=artifacts)
