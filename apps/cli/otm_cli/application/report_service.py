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
from otm_cli.application.analysis_match import (
    require_analysis_matches_document,
    require_baseline_describes_same_system,
)
from otm_cli.reporting import export_full_report_markdown
from otm_cli.shared.document_loader import load_otm_document, load_pack_or_raise
from otm_cli.shared.errors import CliUserError
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
    #: Set when the PDF could not be built in the locale the caller asked for, so the command
    #: layer can say so instead of shipping an English document under a pt-BR request.
    locale_notice: str | None = None


#: The premium HTML template renders every heading and label from English literals — unlike the
#: Markdown renderer, `render_premium_html` never reads `payload.locale`. Building the payload in
#: pt-BR behind that template yields a document that changes language mid-sentence, so the PDF is
#: built in English deliberately. The caller is told; it is no longer discarded in silence.
_PDF_BUILD_LOCALE = "en"


def _reject_premium_only_flags_without_level(
    *,
    report_format: PremiumReportFormat,
    baseline_json: Path | None,
    locale: str | None,
) -> None:
    """Refuse flags the legacy branch cannot honour instead of discarding them.

    Without `--level` this function's caller returns before `report_format`, `--locale` and
    `--baseline` are ever read. `-f pdf` therefore used to write Markdown bytes into the `.pdf`
    path the user named, print a success line and exit 0 — a corrupt deliverable in an evidence
    pack, with nothing on screen to suggest it. Refusing is the only option that neither lies
    about the artifact nor silently substitutes a different one.
    """
    requested = []
    if report_format == PremiumReportFormat.PDF:
        requested.append("--format pdf")
    if locale is not None:
        requested.append("--locale")
    if baseline_json is not None:
        requested.append("--baseline")
    if not requested:
        return
    raise CliUserError(
        exit_code=2,
        failed="`otm report` without `--level`.",
        cause=f"{', '.join(requested)} applies to the premium report only.",
        next_step=("add `--level executive|standard|deep`, or drop the flag for the legacy Markdown report."),
    )


def _pdf_locale_notice(requested_locale: str, build_locale: str) -> str | None:
    """Say that the PDF is not in the requested locale, or stay quiet when it is."""
    if requested_locale == build_locale:
        return None
    return (
        f"`--locale {requested_locale}` was not applied: the premium PDF renders its structural "
        f"text in {build_locale}. Use `--format markdown` for a {requested_locale} report."
    )


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
    if level is None:
        _reject_premium_only_flags_without_level(
            report_format=report_format,
            baseline_json=baseline_json,
            locale=locale,
        )
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
        require_analysis_matches_document(doc, result, flag="--analysis-json")
    else:
        result = analyze_document(doc, pack=pack_def)

    if level is None:
        text = export_full_report_markdown(doc, result)
        return ReportLegacyResult(text=text)

    baseline: AnalysisResult | None = None
    if baseline_json:
        baseline = load_analysis_result_from_path(baseline_json)
        # Not `require_analysis_matches_document`: a baseline is an analysis of an *earlier
        # revision* of this model, so demanding that it describe the current revision refused
        # every legitimate use of the flag — a renamed title, or the added component the
        # baseline section exists to show — and the refusal cost the user the whole report.
        require_baseline_describes_same_system(result, baseline, flag="--baseline")

    requested_locale = normalize_premium_locale(locale)
    is_pdf = report_format == PremiumReportFormat.PDF
    build_locale = _PDF_BUILD_LOCALE if is_pdf else requested_locale
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
    except ImportError as e:
        # The renderer's own ImportError text is Portuguese and unstructured; re-raising it
        # verbatim made the first error after the documented bare install the only non-English
        # message in the CLI. Restate it in this layer's standard three-line shape.
        raise CliUserError(
            exit_code=1,
            failed="PDF output for the premium report.",
            cause="the optional `xhtml2pdf` package is not installed.",
            next_step='install the extra: `pip install "open-threat-model[report]"`.',
        ) from e
    return ReportPremiumPdfResult(
        pdf_bytes=pdf_bytes,
        default_path=Path("report-premium.pdf"),
        locale_notice=_pdf_locale_notice(requested_locale, build_locale),
    )
