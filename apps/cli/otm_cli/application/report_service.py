"""Application use case for generating a risk report."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from otm_report_premium import (
    PdfSupportUnavailable,
    build_premium_report_payload,
    html_to_pdf_bytes,
    render_premium_html,
    render_premium_markdown,
    render_risk_report_markdown,
    render_risk_report_pdf,
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
from otm_cli.application.engine_refusals import engine_refusals_as_cli_errors
from otm_cli.shared.document_loader import load_otm_document, load_pack_or_raise
from otm_cli.shared.errors import CliUserError
from otm_cli.shared.version_util import installed_version


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
) -> ReportPremiumMarkdownResult | ReportPremiumPdfResult:
    level = level or PremiumReportLevel.STANDARD
    default_report = level == PremiumReportLevel.STANDARD
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
        with engine_refusals_as_cli_errors(failed=f"the report for `{path}`."):
            result = analyze_document(doc, pack=pack_def)

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
    build_locale = _PDF_BUILD_LOCALE if is_pdf and not default_report else requested_locale
    payload = build_premium_report_payload(
        doc,
        result,
        level=level,
        baseline=baseline,
        app_version=installed_version(),
        locale=build_locale,
        consolidated=default_report,
    )
    if not is_pdf:
        text = (
            render_risk_report_markdown(payload, doc, analysis_generated=analysis_json is None)
            if default_report
            else render_premium_markdown(payload)
        )
        return ReportPremiumMarkdownResult(text=text)

    try:
        pdf_bytes = (
            render_risk_report_pdf(payload, doc, analysis_generated=analysis_json is None)
            if default_report
            else html_to_pdf_bytes(render_premium_html(payload))
        )
    except PdfSupportUnavailable as e:
        # The renderer now names the reason and the remedy, in English and already split into the
        # two halves this layer prints. Restating them here hard-coded the "not installed" case
        # and would tell someone whose `[report]` extra is satisfied — but whose native Cairo
        # library is missing — to install the extra they already have.
        raise CliUserError(
            exit_code=1,
            failed="PDF output for the risk report.",
            cause=e.cause,
            next_step=e.next_step,
        ) from e
    except ImportError as e:
        # Kept as a net under the branch above. The renderer's own `ImportError` text is
        # Portuguese and unstructured, and letting any import failure it does not classify escape
        # is how the missing-Cairo `OSError` became a raw traceback in the first place.
        raise CliUserError(
            exit_code=1,
            failed="PDF output for the risk report.",
            cause="the optional PDF support could not be loaded.",
            next_step='install the extra: `pip install "open-threat-model[report]"`.',
        ) from e
    return ReportPremiumPdfResult(
        pdf_bytes=pdf_bytes,
        default_path=Path("report-premium.pdf"),
        locale_notice=_pdf_locale_notice(requested_locale, build_locale),
    )
