"""`--level deep --format pdf` must not silently render the standard report.

`docs/features/PREMIUM_REPORTS.md` defines deep as standard "+ apêndice técnico (listagem de
ameaças)", and `--level deep --format pdf` is a documented, allowed combination on the CLI, the
API (`level: deep`, `output_format: pdf`) and the web Export screen. It produced a PDF whose
extracted text was character-identical to the standard one — 8 pages / 8654 chars either way on
`examples/saas-ordering-v1.otm.yaml` — while the Markdown pair differed by 5.3 KB.

Cause: every level branch in `render_html.py` tested `!= ReportLevel.EXECUTIVE`, and the file
never mentioned `technical_appendix`. The builder had been attaching the appendix to the payload
all along, so only the HTML path dropped it — which is why the same defect showed up in the CLI,
the API and the browser at once. Fixed in the renderer, not at a call site.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from otm_report_premium import build_premium_report_payload
from otm_report_premium.enums import ReportLevel
from otm_report_premium.models import PremiumReportPayload
from otm_report_premium.render_html import render_premium_html
from otm_threat_engine import analyze_document

_MODEL = Path(__file__).resolve().parents[1] / "examples" / "saas-ordering-v1.otm.yaml"


@pytest.fixture
def document() -> ThreatModelDocument:
    return load_document_from_yaml_path(_MODEL)


def _payload(document: ThreatModelDocument, level: ReportLevel) -> PremiumReportPayload:
    return build_premium_report_payload(document, analyze_document(document), level=level)


def _html(document: ThreatModelDocument, level: ReportLevel) -> str:
    return render_premium_html(_payload(document, level))


def test_the_deep_html_differs_from_the_standard_html(document: ThreatModelDocument) -> None:
    """The exact equality the bug measured, one step upstream of the PDF bytes."""
    assert _html(document, ReportLevel.DEEP) != _html(document, ReportLevel.STANDARD)


def test_the_deep_html_carries_the_technical_appendix(document: ThreatModelDocument) -> None:
    assert "<h2>Technical appendix</h2>" in _html(document, ReportLevel.DEEP)


def test_the_standard_html_does_not(document: ThreatModelDocument) -> None:
    assert "Technical appendix" not in _html(document, ReportLevel.STANDARD)


def test_the_executive_html_does_not(document: ThreatModelDocument) -> None:
    assert "Technical appendix" not in _html(document, ReportLevel.EXECUTIVE)


def test_the_appendix_lists_the_heuristic_threats(document: ThreatModelDocument) -> None:
    """One row per threat id — the content the deep Markdown has and the deep PDF had not."""
    payload = _payload(document, ReportLevel.DEEP)
    html = render_premium_html(payload)
    first_threat_id = payload.top_risks[0].threat_id

    assert f"<td>{first_threat_id}" in html


def test_the_appendix_carries_the_methodology_note(document: ThreatModelDocument) -> None:
    payload = _payload(document, ReportLevel.DEEP)
    assert payload.technical_appendix is not None  # payload precondition, not the assertion
    note = payload.technical_appendix.methodology_outputs_note

    assert note in render_premium_html(payload)


def test_the_appendix_survives_an_import_evidence_note(document: ThreatModelDocument) -> None:
    payload = _payload(document, ReportLevel.DEEP)
    assert payload.technical_appendix is not None  # payload precondition, not the assertion
    payload.technical_appendix.import_evidence_note = "Imported from terraform plan"

    assert "Imported from terraform plan" in render_premium_html(payload)


def test_a_deep_payload_without_an_appendix_renders_no_section(document: ThreatModelDocument) -> None:
    """`technical_appendix` is optional on the model, so the renderer must tolerate None."""
    payload = _payload(document, ReportLevel.DEEP)
    payload.technical_appendix = None

    assert "Technical appendix" not in render_premium_html(payload)


def test_a_long_appendix_is_capped_and_says_so(document: ThreatModelDocument) -> None:
    """A 200-component model would otherwise turn the PDF into hundreds of rows."""
    payload = _payload(document, ReportLevel.DEEP)
    assert payload.technical_appendix is not None  # payload precondition, not the assertion
    payload.technical_appendix.full_threat_listing = "\n".join(f"### t{i} - Title {i}\nBody {i}\n" for i in range(80))
    payload.technical_appendix.total_threat_count = 80

    assert "20 further threat(s) omitted from the PDF appendix" in render_premium_html(payload)


def test_a_short_appendix_says_nothing_about_omissions(document: ThreatModelDocument) -> None:
    payload = _payload(document, ReportLevel.DEEP)
    assert payload.technical_appendix is not None  # payload precondition, not the assertion
    payload.technical_appendix.full_threat_listing = "### t1 - Only one\nBody\n"
    # Both halves of the fixture, or the payload says "one entry listed, forty produced" and the
    # renderer is right to disclose the other thirty-nine.
    payload.technical_appendix.total_threat_count = 1

    assert "omitted from the PDF appendix" not in render_premium_html(payload)


def test_an_appendix_entry_keeps_its_description(document: ThreatModelDocument) -> None:
    payload = _payload(document, ReportLevel.DEEP)
    assert payload.technical_appendix is not None  # payload precondition, not the assertion
    payload.technical_appendix.full_threat_listing = "### t1 - Heading\n\nfirst line\nsecond line\n"

    assert "<td>first line second line</td>" in render_premium_html(payload)


def test_appendix_text_is_escaped(document: ThreatModelDocument) -> None:
    """Threat titles are attacker-influenced; the appendix must not open a markup hole."""
    payload = _payload(document, ReportLevel.DEEP)
    assert payload.technical_appendix is not None  # payload precondition, not the assertion
    payload.technical_appendix.full_threat_listing = "### <script>alert(1)</script>\nbody\n"

    assert "<script>" not in render_premium_html(payload)


def test_an_empty_appendix_listing_renders_an_empty_table(document: ThreatModelDocument) -> None:
    payload = _payload(document, ReportLevel.DEEP)
    assert payload.technical_appendix is not None  # payload precondition, not the assertion
    payload.technical_appendix.full_threat_listing = ""

    assert "<h2>Technical appendix</h2>" in render_premium_html(payload)
