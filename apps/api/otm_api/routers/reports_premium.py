"""Report premium (executive / standard / deep) — Markdown ou PDF."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import PlainTextResponse, Response
from otm_report_premium.enums import ReportFormat, ReportLevel
from otm_report_premium.i18n_locale import normalize_premium_locale
from otm_report_premium.report_i18n import premium_error_analysis_required
from otm_threat_engine import AnalysisResult
from pydantic import ValidationError as PydanticValidationError

from otm_api.error_models import API_ERROR_RESPONSES
from otm_api.routers._errors import (
    document_from_payload_or_422,
    ensure_analysis_matches_document,
    ensure_baseline_describes_same_system,
    error_detail,
    raise_analysis_validation_error,
    raise_pack_not_found,
)
from otm_api.schemas.bodies import PremiumReportBody
from otm_api.services.analysis import run_analysis
from otm_api.services.reports_premium import render_premium

router = APIRouter(prefix="/reports", tags=["Reports"], responses=API_ERROR_RESPONSES)


@router.post(
    "/premium",
    summary="Premium report (Markdown or PDF)",
    description=(
        "Builds the consolidated premium report from analysis, backlog, diff, and explainability. "
        "Requires `document` and either `analysis` or `run_analysis: true`."
    ),
    response_model=None,
    responses={
        200: {
            "description": "Corpo = Markdown (`output_format=markdown`) ou PDF binário (`output_format=pdf`).",
            "content": {
                "text/markdown": {"schema": {"type": "string"}},
                "application/pdf": {"schema": {"type": "string", "format": "binary"}},
            },
        },
    },
)
def post_premium_report(body: PremiumReportBody) -> PlainTextResponse | Response:
    loc = normalize_premium_locale(body.locale)
    doc = document_from_payload_or_422(body.document)
    analysis_obj: AnalysisResult | None = None
    if body.analysis is not None:
        try:
            analysis_obj = AnalysisResult.model_validate(body.analysis)
        except PydanticValidationError as e:
            raise raise_analysis_validation_error(e) from e
        ensure_analysis_matches_document(doc, analysis_obj)

    # `baseline_analysis` fica de fora da guarda de *mesma revisão*: é, por definição, a análise
    # de uma versão anterior do modelo — a divergência é o conteúdo da secção baseline/diff, não
    # um erro. Fora dessa guarda não é fora de guarda nenhuma, e a distinção faltava aqui: a
    # pergunta certa para um baseline é "mesmo sistema?", verificada mais abaixo, assim que a
    # análise actual existir para comparar. Ver `ensure_baseline_describes_same_system`.
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
                    message=premium_error_analysis_required(loc),
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
            raise raise_pack_not_found(body.pack_id) from e

    # Depois de `analysis_obj` existir, seja qual for a origem: a relação é entre as duas
    # análises, por isso a guarda tem de correr tanto para `analysis` enviado como para
    # `run_analysis: true`, e não pode correr antes.
    if baseline_obj is not None:
        ensure_baseline_describes_same_system(analysis_obj, baseline_obj)

    level = ReportLevel(body.level)
    fmt = ReportFormat(body.output_format)

    try:
        md, pdf = render_premium(
            doc,
            analysis_obj,
            level=level,
            output_format=fmt,
            baseline=baseline_obj,
            locale=loc,
        )
    except ImportError as e:  # pragma: no cover - defensive: PDF extra (xhtml2pdf) installed in supported envs
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=error_detail(
                code="PDF_DEPENDENCY",
                message=str(e),
            ),
        ) from e

    if fmt == ReportFormat.MARKDOWN:
        return PlainTextResponse(md, media_type="text/markdown; charset=utf-8")
    assert pdf is not None  # type narrowing; pdf is always set for the non-Markdown branch  # nosec B101
    return Response(content=pdf, media_type="application/pdf")
