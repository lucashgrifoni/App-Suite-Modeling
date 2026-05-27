"""Coverage — premium report rendering across levels, formats, locales, and baseline/diff.

Exercises render_html / render_markdown / builder / methodology / branding / risk_context
by rendering every level x format x locale on a rich model, with and without a baseline.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest as _pytest
from otm_core_schema import load_document_from_yaml_path

_pytest.importorskip("fastapi")
from otm_api.services.reports_premium import render_premium  # noqa: E402
from otm_report_premium.enums import ReportFormat, ReportLevel  # noqa: E402
from otm_threat_engine import analyze_document  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]
_RICH = _ROOT / "examples" / "saas-ordering-v1.otm.yaml"
_MIN = _ROOT / "examples" / "minimal.otm.yaml"

_HAS_PDF = True
try:  # xhtml2pdf is an optional extra
    import xhtml2pdf  # noqa: F401
except Exception:  # pragma: no cover - environment without the report extra
    _HAS_PDF = False


def _analysis(model: Path):
    return analyze_document(load_document_from_yaml_path(model))


_REPORT_MODELS = [
    _RICH,
    _ROOT / "examples" / "test-apps" / "finance-wallet.otm.yaml",
    _ROOT / "examples" / "test-apps" / "health-clinic.otm.yaml",
    _ROOT / "examples" / "plot4ai-calibration" / "otm-ai-002-rag-enterprise.otm.yaml",
]


@pytest.mark.parametrize("model", _REPORT_MODELS)
@pytest.mark.parametrize("level", [ReportLevel.EXECUTIVE, ReportLevel.STANDARD, ReportLevel.DEEP])
@pytest.mark.parametrize("locale", ["pt-BR", "en"])
def test_render_markdown_all_levels_locales(model: Path, level: ReportLevel, locale: str) -> None:
    doc = load_document_from_yaml_path(model)
    analysis = _analysis(model)
    md, pdf = render_premium(
        doc, analysis, level=level, output_format=ReportFormat.MARKDOWN, locale=locale
    )
    assert md and isinstance(md, str)
    assert pdf is None


def test_render_markdown_with_baseline_diff() -> None:
    doc = load_document_from_yaml_path(_RICH)
    analysis = _analysis(_RICH)
    baseline = _analysis(_MIN)
    md, _ = render_premium(
        doc, analysis, level=ReportLevel.DEEP, output_format=ReportFormat.MARKDOWN, baseline=baseline, locale="pt-BR"
    )
    assert md


def _profiled_doc(model: str, profile: str, tags: list[str]):
    from otm_core_schema import ThreatModelDocument

    doc = load_document_from_yaml_path(_ROOT / model)
    d = doc.model_dump(mode="python", by_alias=True)
    d.setdefault("model", {})["template_semantic_profile"] = profile
    meta = d.setdefault("metadata", {})
    meta["tags"] = list(meta.get("tags") or []) + tags
    return ThreatModelDocument.model_validate(d)


@pytest.mark.skipif(not _HAS_PDF, reason="xhtml2pdf extra not installed")
def test_deep_pdf_with_audit_sections() -> None:
    doc = _profiled_doc(
        "examples/test-apps/ecommerce-subscription.otm.yaml",
        "industry_ecommerce",
        ["wz:industry_ecommerce:checkout=no", "wz:industry_ecommerce:psp_boundary=no"],
    )
    analysis = analyze_document(doc)
    _, pdf = render_premium(doc, analysis, level=ReportLevel.DEEP, output_format=ReportFormat.PDF, locale="en")
    assert pdf and len(pdf) > 100


@pytest.mark.parametrize("locale", ["pt-BR", "en"])
def test_deep_report_with_audit_sections(locale: str) -> None:
    # Profile + wizard tags + anti-pattern structure -> audit section (wizard notes, anti-patterns,
    # model gaps) is populated, exercising the deep-level render branches.
    doc = _profiled_doc(
        "examples/test-apps/ecommerce-subscription.otm.yaml",
        "industry_ecommerce",
        ["wz:industry_ecommerce:checkout=no", "wz:industry_ecommerce:psp_boundary=no"],
    )
    analysis = analyze_document(doc)
    md, _ = render_premium(doc, analysis, level=ReportLevel.DEEP, output_format=ReportFormat.MARKDOWN, locale=locale)
    assert md and "##" in md


def test_report_logo_data_uri_branches(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from otm_report_premium.branding import report_logo_data_uri

    png = tmp_path / "logo.png"
    # minimal but non-empty PNG header bytes
    png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 32)

    # env var → valid small file returns a data URI
    monkeypatch.setenv("OTM_PREMIUM_LOGO_PATH", str(png))
    uri = report_logo_data_uri()
    assert uri is not None and uri.startswith("data:image/png;base64,")

    # too-large file is skipped (falls back to packaged asset or None)
    res_small_limit = report_logo_data_uri(max_bytes=1)
    assert res_small_limit is None or res_small_limit.startswith("data:image/png;base64,")

    # nonexistent env path is skipped
    monkeypatch.setenv("OTM_PREMIUM_LOGO_PATH", str(tmp_path / "missing.png"))
    _ = report_logo_data_uri()

    # no env var → default/packaged resolution path
    monkeypatch.delenv("OTM_PREMIUM_LOGO_PATH", raising=False)
    _ = report_logo_data_uri()


def test_methodology_voice_lines_all_methodologies_both_locales() -> None:
    from otm_core_schema import ThreatModelMethodology
    from otm_report_premium.methodology import methodology_voice_lines

    for m in ThreatModelMethodology:
        for loc in ("en", "pt-BR"):
            lines = methodology_voice_lines(m, loc)  # type: ignore[arg-type]
            assert lines and all(isinstance(x, str) for x in lines)


@pytest.mark.skipif(not _HAS_PDF, reason="xhtml2pdf extra not installed")
@pytest.mark.parametrize("level", [ReportLevel.EXECUTIVE, ReportLevel.STANDARD, ReportLevel.DEEP])
def test_render_pdf_all_levels(level: ReportLevel) -> None:
    doc = load_document_from_yaml_path(_RICH)
    analysis = _analysis(_RICH)
    md, pdf = render_premium(doc, analysis, level=level, output_format=ReportFormat.PDF, locale="en")
    assert pdf is not None and isinstance(pdf, (bytes, bytearray)) and len(pdf) > 100
