"""Use case: legacy or premium report."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from otm_report_premium import (
    build_premium_report_payload,
    html_to_pdf_bytes,
    render_premium_html,
    render_premium_markdown,
)
from otm_report_premium.enums import ReportFormat as PremiumReportFormat
from otm_report_premium.enums import ReportLevel as PremiumReportLevel
from otm_report_premium.i18n_locale import normalize_premium_locale
from otm_threat_engine import AnalysisResult, analyze_document

from otm_cli.application.analysis_io import load_analysis_result_from_path
from otm_cli.reporting import export_full_report_markdown
from otm_cli.shared.document_loader import load_otm_document, load_pack_or_raise
from otm_cli.shared.version_util import installed_version


@dataclass
class ReportLegacyResult:
    text: str


@dataclass
class ReportPremiumMarkdownResult:
    text: str


@dataclass
class ReportPremiumPdfResult:
    pdf_bytes: bytes
    default_path: Path


class ReportPdfDependencyError(Exception):
    """Missing dependency for PDF (e.g. `report` extra)."""


def run_report(
    path: Path,
    *,
    pack: str | None,
    level: PremiumReportLevel | None,
    report_format: PremiumReportFormat,
    analysis_json: Path | None,
    baseline_json: Path | None,
    locale: str | None = None,
) -> ReportLegacyResult | ReportPremiumMarkdownResult | ReportPremiumPdfResult:
    doc = load_otm_document(
        path,
        failed=f"report generation for `{path}`.",
        validation_next_step="run `otm validate` and fix errors before generating the report.",
        runtime_next_step="confirm path and YAML integrity.",
    )
    pack_def = None
    if pack:
        pack_def = load_pack_or_raise(
            pack_id=pack,
            failed=f"loading pack `{pack}`.",
            next_step="run `otm packs` and retry with a valid pack ID.",
        )

    if analysis_json:
        result = load_analysis_result_from_path(analysis_json)
    else:
        result = analyze_document(doc, pack=pack_def)

    if level is None:
        text = export_full_report_markdown(doc, result)
        return ReportLegacyResult(text=text)

    baseline: AnalysisResult | None = None
    if baseline_json:
        baseline = load_analysis_result_from_path(baseline_json)

    build_locale = "en" if report_format == PremiumReportFormat.PDF else normalize_premium_locale(locale)
    payload = build_premium_report_payload(
        doc,
        result,
        level=level,
        baseline=baseline,
        app_version=installed_version(),
        locale=build_locale,
    )
    if report_format == PremiumReportFormat.MARKDOWN:
        return ReportPremiumMarkdownResult(text=render_premium_markdown(payload))

    html = render_premium_html(payload)
    try:
        pdf_bytes = html_to_pdf_bytes(html)
    except ImportError as e:  # pragma: no cover - defensive: report PDF extra installed in supported envs
        raise ReportPdfDependencyError(str(e)) from e
    return ReportPremiumPdfResult(pdf_bytes=pdf_bytes, default_path=Path("report-premium.pdf"))
