"""Actionable remediation backlog from model + analysis."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Query
from fastapi.responses import PlainTextResponse
from otm_threat_engine import AnalysisResult
from pydantic import ValidationError as PydanticValidationError

from otm_api.routers._errors import (
    document_from_payload_or_422,
    raise_analysis_validation_error,
)
from otm_api.schemas.bodies import RemediationBacklogRequest
from otm_api.services.remediation import build_remediation_backlog_response

router = APIRouter(prefix="/remediation", tags=["Remediation"])


@router.post(
    "/backlog",
    summary="Generate remediation backlog",
    description=(
        "Body: canonical `document`; optional `analysis` (`AnalysisResult`). "
        "If `analysis` is omitted, set `run_analysis: true` to run the engine."
    ),
)
def post_remediation_backlog(
    body: RemediationBacklogRequest,
    export_format: Literal["json", "markdown"] = Query(
        default="json",
        alias="format",
        description="json = full object; markdown = human-readable report.",
    ),
    group_by: str | None = Query(
        default=None,
        description="For Markdown: root-cause | control | category.",
    ),
) -> Any:
    doc = document_from_payload_or_422(body.document)
    analysis_obj: AnalysisResult | None = None
    if body.analysis is not None:
        try:
            analysis_obj = AnalysisResult.model_validate(body.analysis)
        except PydanticValidationError as e:
            raise raise_analysis_validation_error(e) from e

    backlog = build_remediation_backlog_response(
        doc,
        analysis_obj,
        run_analysis=body.run_analysis,
        pack_id=body.pack_id,
        methodology=body.methodology,
        auto_recommend_methodology=body.auto_recommend_methodology,
    )
    if export_format == "markdown":
        from otm_exporters import export_remediation_backlog_markdown

        text = export_remediation_backlog_markdown(backlog, group_by=group_by)
        return PlainTextResponse(text, media_type="text/markdown; charset=utf-8")
    return backlog.model_dump(mode="json")
