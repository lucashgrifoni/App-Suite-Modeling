"""Backlog de remediação — documento + análise já validados na camada HTTP."""

from __future__ import annotations

from fastapi import HTTPException, status
from otm_core_schema import ThreatModelDocument, ThreatModelMethodology
from otm_threat_engine import AnalysisResult
from otm_threat_engine.remediation import RemediationBacklog, build_remediation_backlog

from otm_api.routers._errors import error_detail


def build_remediation_backlog_response(
    doc: ThreatModelDocument,
    result: AnalysisResult | None,
    *,
    run_analysis: bool,
    pack_id: str | None,
    methodology: ThreatModelMethodology | None,
    auto_recommend_methodology: bool,
) -> RemediationBacklog:
    """Resolve `AnalysisResult` quando necessário e constrói o backlog."""
    if result is not None:
        return build_remediation_backlog(result, doc)
    if not run_analysis:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_detail(
                code="REMEDIATION_INPUT",
                message="Forneça `analysis` ou defina `run_analysis: true`.",
            ),
        )
    analysis_out = run_analysis(
        doc,
        pack_id=pack_id,
        methodology=methodology,
        auto_recommend_methodology=auto_recommend_methodology,
    )
    return build_remediation_backlog(analysis_out, doc)
