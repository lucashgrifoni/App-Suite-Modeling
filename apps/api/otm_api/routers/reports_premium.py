"""Report premium (executive / standard / deep) — Markdown ou PDF."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import PlainTextResponse, Response
from otm_report_premium.enums import ReportFormat, ReportLevel
from otm_threat_engine import AnalysisResult
from pydantic import ValidationError as PydanticValidationError

from otm_api.routers._errors import (
    document_from_payload_or_422,
    error_detail,
    raise_analysis_validation_error,
    raise_pack_not_found,
)
from otm_api.schemas.bodies import PremiumReportBody
from otm_api.services.analysis import run_analysis
from otm_api.services.reports_premium import render_premium

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post(
    "/premium",
    summary="Premium report (Markdown or PDF)",
    description=(
        "Builds the consolidated premium report from analysis, backlog, diff, and explainability. "
        "Requires `document` and either `analysis` or `run_analysis: true`."
    ),
    response_model=None,
)
def post_premium_report(body: PremiumReportBody) -> Any:
    doc = document_from_payload_or_422(body.document)
    analysis_obj: AnalysisResult | None = None
    if body.analysis is not None:
        try:
            analysis_obj = AnalysisResult.model_validate(body.analysis)
        except PydanticValidationError as e:
            raise raise_analysis_validation_error(e) from e

    baseline_obj: AnalysisResult | None = None
    if body.baseline_analysis is not None:
        try:
            baseline_obj = AnalysisResult.model_validate(body.baseline_analysis)
        except PydanticValidationError as e:
            raise raise_analysis_validation_error(e) from e

    if analysis_obj is None:
        if not body.run_analysis:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_detail(
                    code="PREMIUM_REPORT_INPUT",
                    message="Forneça `analysis` ou defina `run_analysis: true`.",
                ),
            )
        try:
            analysis_obj = run_analysis(
                doc,
                pack_id=body.pack_id,
                methodology=body.methodology,
                auto_recommend_methodology=body.auto_recommend_methodology,
            )
        except FileNotFoundError as e:
            raise raise_pack_not_found(e) from e

    level = ReportLevel(body.level)
    fmt = ReportFormat(body.output_format)

    try:
        md, pdf = render_premium(
            doc,
            analysis_obj,
            level=level,
            output_format=fmt,
            baseline=baseline_obj,
        )
    except ImportError as e:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=error_detail(
                code="PDF_DEPENDENCY",
                message=str(e),
            ),
        ) from e

    if fmt == ReportFormat.MARKDOWN:
        return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")
    assert pdf is not None
    return Response(content=pdf, media_type="application/pdf")