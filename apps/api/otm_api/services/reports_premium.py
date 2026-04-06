"""Geração de report premium — delega a `otm_report_premium` (sem lógica duplicada)."""

from __future__ import annotations

import importlib.metadata

from otm_core_schema import ThreatModelDocument
from otm_report_premium import (
    build_premium_report_payload,
    html_to_pdf_bytes,
    render_premium_html,
    render_premium_markdown,
)
from otm_report_premium.enums import ReportFormat, ReportLevel
from otm_threat_engine import AnalysisResult


def app_version() -> str:
    try:
        return importlib.metadata.version("open-threat-model")
    except importlib.metadata.PackageNotFoundError:
        return "dev"


def render_premium(
    doc: ThreatModelDocument,
    analysis: AnalysisResult,
    *,
    level: ReportLevel,
    output_format: ReportFormat,
    baseline: AnalysisResult | None = None,
    locale: str | None = None,
) -> tuple[str, bytes | None]:
    """
    Devolve (markdown, pdf_bytes ou None).

    PDF só é gerado quando `output_format` é PDF (Markdown não é calculado nesse caso).
    """
    payload = build_premium_report_payload(
        doc,
        analysis,
        level=level,
        baseline=baseline,
        app_version=app_version(),
        locale=locale,
    )
    if output_format == ReportFormat.MARKDOWN:
        return render_premium_markdown(payload), None
    html = render_premium_html(payload)
    return "", html_to_pdf_bytes(html)
