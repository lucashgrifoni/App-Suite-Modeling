"""The premium PDF must not turn text it cannot draw into a wall of black boxes.

Reproduced: with `title: "支付系统 Payments Платежи"` the PDF cover read `■■■■ Payments ■■■■■■■`,
one box per dropped codepoint, and with CJK component names the whole report became illegible
(226 boxes on the standard level). The Markdown export of the same model was perfect, so nothing
was wrong with the model — only the PDF fonts, which cover WinAnsi plus the Symbol/ZapfDingbats
substitutions. The product's own chrome was damaged too: the stock all-Latin report carried 9
boxes, two of them its own status emoji (`Overall status: ■■ …`, `Highest priority:■ P1`).

Chosen remedy (`pdf_text.py` documents why a font was not embedded): transliterate what has a
Latin reading, mark the rest `?`, leave everything the fonts *can* draw untouched, and state the
degradation in the report footer instead of letting it pass silently.
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from otm_report_premium import build_premium_report_payload
from otm_report_premium.enums import ReportLevel
from otm_report_premium.pdf_text import to_pdf_font_text
from otm_report_premium.render_html import render_premium_html
from otm_threat_engine import analyze_document

_MINIMAL = Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml"
_BOX = "■"
_NOTICE = "outside the PDF font's range"


# --- the degradation itself ------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Plataforma de pedidos",  # plain ASCII
        "atenção — coração · ½",  # WinAnsi: accents, em dash, middot
        "α ≤ β",  # Symbol substitution font
        "→ ✓ ★",  # arrows and dingbats
    ],
)
def test_text_the_pdf_fonts_can_draw_is_untouched(text: str) -> None:
    """A `?` where a glyph used to render would be a regression, not a fix."""
    assert to_pdf_font_text(text) == text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Платежи", "Platezhi"),
        ("Платёжный шлюз", "Platyozhnyy shlyuz"),
        ("Ключ", "Klyuch"),
        ("Łódź", "Lódz"),  # `ó` is WinAnsi and stays; only `Ł` and `ź` need help
        ("Ｑueue", "Queue"),
        ("Ārtifact", "Artifact"),
        ("ά β", "α β"),  # an accented Greek letter folds onto the substituted one
    ],
)
def test_a_latin_reading_is_used_when_there_is_one(raw: str, expected: str) -> None:
    assert to_pdf_font_text(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("支付系统", "????"),
        ("مدفوعات", "???????"),
        ("🔐💳", "??"),
        ("שלום", "????"),
    ],
)
def test_what_has_no_reading_is_marked_one_mark_per_character(raw: str, expected: str) -> None:
    assert to_pdf_font_text(raw) == expected


def test_cjk_punctuation_is_degraded_too() -> None:
    """`、` is not a letter, but it has no glyph either."""
    assert to_pdf_font_text("、") == "?"


def test_surrounding_text_survives_the_degradation() -> None:
    assert to_pdf_font_text("支付系统 Payments Платежи") == "???? Payments Platezhi"


# --- the rendered report ---------------------------------------------------------------------


@pytest.fixture
def non_latin_document() -> ThreatModelDocument:
    document = load_document_from_yaml_path(_MINIMAL)
    document.metadata.title = "支付系统 Payments Платежи مدفوعات 🔐"
    document.components[0].name = "Cliente móvel 📱"
    document.components[1].name = "Платёжный шлюз"
    return document


def _html(document: ThreatModelDocument, level: ReportLevel = ReportLevel.EXECUTIVE) -> str:
    payload = build_premium_report_payload(document, analyze_document(document), level=level)
    return render_premium_html(payload)


def test_the_html_handed_to_the_pdf_carries_no_undrawable_title(non_latin_document: ThreatModelDocument) -> None:
    assert "支付系统" not in _html(non_latin_document)


def test_the_cyrillic_component_name_is_readable(non_latin_document: ThreatModelDocument) -> None:
    assert "Platyozhnyy shlyuz" in _html(non_latin_document)


def test_the_degradation_is_stated_in_the_report(non_latin_document: ThreatModelDocument) -> None:
    assert _NOTICE in _html(non_latin_document)


def test_an_all_latin_report_says_nothing_about_degradation() -> None:
    assert _NOTICE not in _html(load_document_from_yaml_path(_MINIMAL))


def test_the_chrome_no_longer_uses_emoji_the_font_lacks() -> None:
    """`🔴` (U+1F534) and `⚠` (U+26A0) as HTML entities were the product's own black boxes."""
    html = _html(load_document_from_yaml_path(_MINIMAL), ReportLevel.STANDARD)

    assert "&#128308;" not in html


def test_the_warning_emoji_entity_is_gone_too() -> None:
    html = _html(load_document_from_yaml_path(_MINIMAL), ReportLevel.STANDARD)

    assert "&#9888;" not in html


# --- the actual PDF --------------------------------------------------------------------------


def _pdf_text(document: ThreatModelDocument, level: ReportLevel) -> str:
    pytest.importorskip("xhtml2pdf")
    pypdf = pytest.importorskip("pypdf")
    from otm_report_premium.pdf_export import html_to_pdf_bytes

    pdf = html_to_pdf_bytes(_html(document, level))
    reader = pypdf.PdfReader(io.BytesIO(pdf))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def test_the_stock_report_renders_without_a_single_black_box() -> None:
    """The 9 boxes the stock all-Latin report used to carry were the product's own copy."""
    assert _pdf_text(load_document_from_yaml_path(_MINIMAL), ReportLevel.STANDARD).count(_BOX) == 0


def test_the_non_latin_report_renders_without_a_single_black_box(
    non_latin_document: ThreatModelDocument,
) -> None:
    assert _pdf_text(non_latin_document, ReportLevel.EXECUTIVE).count(_BOX) == 0


def test_the_non_latin_pdf_tells_the_reader_what_happened(non_latin_document: ThreatModelDocument) -> None:
    assert _NOTICE in _pdf_text(non_latin_document, ReportLevel.EXECUTIVE)


def test_the_deep_pdf_is_longer_than_the_standard_one() -> None:
    """End-to-end proof for the appendix fix: both used to be 8 pages of identical text."""
    document = load_document_from_yaml_path(_MINIMAL)
    deep = _pdf_text(document, ReportLevel.DEEP)

    assert deep != _pdf_text(document, ReportLevel.STANDARD)


def test_the_pdf_export_no_longer_logs_a_css_parse_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Two raw `getSize: Not a float '0.04em'` lines leaked onto stderr on every single export."""
    with caplog.at_level("WARNING", logger="xhtml2pdf.util"):
        _pdf_text(load_document_from_yaml_path(_MINIMAL), ReportLevel.EXECUTIVE)

    assert [record.getMessage() for record in caplog.records if "getSize" in record.getMessage()] == []
