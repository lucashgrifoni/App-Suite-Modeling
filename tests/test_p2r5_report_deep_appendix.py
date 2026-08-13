"""Round-5: `--level deep` must not cut its appendix mid-word, nor lie about what it left out.

Two reports of the same defect, fixed together because they are the same arithmetic:

* The Markdown appendix was cut twice — the builder sliced the listing at 120 000 characters and
  the renderer sliced *that* at 20 000 more, landing inside a word (`… Component 27 / Ameaça
  STRIDE para 'Component 27' (svc) como`) immediately before `</details>`. 126 of 4302 threats
  reached the file with no count and nothing to distinguish it from a corrupted artifact.
* The HTML/PDF appendix then printed `685 further threat(s) omitted` when 4242 were, because it
  counted against the listing it had been handed — the one the builder had already shortened —
  and redirected the reader to "the Markdown report for the complete listing", which was the
  shorter of the two.

The contract now: one cut, taken at an entry boundary; both renderers state N of M against what
the analysis actually produced; and the redirect names the artifact that really holds everything.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from otm_core_schema import StrideCategory, Threat, ThreatModelDocument, load_document_from_yaml_path
from otm_report_premium import build_premium_report_payload, render_premium_html, render_premium_markdown
from otm_report_premium.enums import ReportLevel
from otm_report_premium.models import APPENDIX_ENTRY_PREFIX, PremiumReportPayload, count_appendix_entries
from otm_threat_engine import analyze_document

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"

#: Enough canonical threats, each verbose enough, to blow past the builder's 120 000-char budget
#: while still leaving more than the PDF's 60 rows standing — the shape the bug was reported in —
#: without needing a 500-component model and the seconds of analysis it costs.
_OVERSIZE_THREATS = 200
_OVERSIZE_BODY = "palavra " * 130


def _document(threats: list[Threat]) -> ThreatModelDocument:
    doc = load_document_from_yaml_path(_MINIMAL)
    return doc.model_copy(update={"threats": threats})


def _payload(doc: ThreatModelDocument, locale: str = "en") -> PremiumReportPayload:
    return build_premium_report_payload(
        doc, analyze_document(doc), level=ReportLevel.DEEP, app_version="t", locale=locale
    )


@pytest.fixture
def small() -> PremiumReportPayload:
    return _payload(_document([]))


@pytest.fixture
def oversize() -> PremiumReportPayload:
    return _payload(
        _document(
            [
                Threat(
                    id=f"t{i}",
                    title=f"Canonical threat {i}",
                    description=f"{_OVERSIZE_BODY}fim-da-entrada-{i}",
                    stride=StrideCategory.TAMPERING,
                    target_component_id="api",
                )
                for i in range(_OVERSIZE_THREATS)
            ]
        )
    )


def _appendix(payload: PremiumReportPayload):
    appendix = payload.technical_appendix
    assert appendix is not None  # deep always carries one; this is the fixture premise
    return appendix


def test_the_total_counts_every_threat_the_analysis_produced(small: PremiumReportPayload) -> None:
    appendix = _appendix(small)

    assert appendix.total_threat_count == count_appendix_entries(appendix.full_threat_listing)


def test_an_oversize_listing_is_shortened(oversize: PremiumReportPayload) -> None:
    """Premise of the tests below: this payload really does overflow the budget."""
    appendix = _appendix(oversize)

    assert count_appendix_entries(appendix.full_threat_listing) < appendix.total_threat_count


def test_the_shortened_listing_stops_at_an_entry_boundary(oversize: PremiumReportPayload) -> None:
    """The reported symptom: the last entry used to end inside a word."""
    listing = _appendix(oversize).full_threat_listing

    last_body = listing.rstrip().splitlines()[-1]
    assert re.search(r"fim-da-entrada-\d+$", last_body), last_body


def test_every_entry_in_the_listing_still_has_its_body(oversize: PremiumReportPayload) -> None:
    """A heading with nothing under it would mean the cut landed between the two lines."""
    lines = _appendix(oversize).full_threat_listing.splitlines()
    headings = [i for i, line in enumerate(lines) if line.startswith(APPENDIX_ENTRY_PREFIX)]

    assert headings
    assert all(i + 1 < len(lines) and lines[i + 1].strip() for i in headings)


def test_the_markdown_no_longer_applies_a_second_cut(oversize: PremiumReportPayload) -> None:
    """One budget, taken once. The renderer used to slice the already-short listing to 20 000."""
    appendix = _appendix(oversize)

    markdown = render_premium_markdown(oversize)

    assert appendix.full_threat_listing in markdown


@pytest.mark.parametrize("locale", ["en", "pt-BR"])
def test_the_markdown_states_how_many_of_how_many(locale: str) -> None:
    doc = _document([])
    payload = _payload(doc, locale)
    appendix = _appendix(payload)

    markdown = render_premium_markdown(payload)

    shown = count_appendix_entries(appendix.full_threat_listing)
    assert str(shown) in markdown
    assert re.search(rf"\b{shown}\b.*\b{appendix.total_threat_count}\b", markdown)


def test_a_shortened_markdown_appendix_points_at_the_complete_artifact(oversize: PremiumReportPayload) -> None:
    markdown = render_premium_markdown(oversize)

    assert "otm analyze --json-out" in markdown


def test_a_complete_markdown_appendix_promises_nothing_else(small: PremiumReportPayload) -> None:
    """The other direction: no redirect when the reader already has everything."""
    appendix = _appendix(small)
    assert count_appendix_entries(appendix.full_threat_listing) == appendix.total_threat_count

    assert "otm analyze --json-out" not in render_premium_markdown(small)


def test_the_pdf_counts_omissions_against_the_analysis_not_the_listing(oversize: PremiumReportPayload) -> None:
    """The 6x undercount: `entries` had already been shortened before it was measured."""
    appendix = _appendix(oversize)

    html = render_premium_html(oversize)

    match = re.search(r"(\d+) further threat\(s\) omitted", html)
    assert match is not None, "an oversize appendix must disclose its omissions"
    omitted = int(match.group(1))
    listed = count_appendix_entries(appendix.full_threat_listing)
    assert omitted == appendix.total_threat_count - min(60, listed)
    assert listed - 60 < omitted  # what measuring inside the shortened listing used to report


def test_the_pdf_redirect_names_an_artifact_that_is_actually_complete(oversize: PremiumReportPayload) -> None:
    """It used to send the reader to the Markdown report, which carried fewer entries than it."""
    html = render_premium_html(oversize)

    assert "export the Markdown report for the complete listing" not in html
    assert "otm analyze --json-out" in html


def test_an_entry_larger_than_the_whole_budget_is_still_shown() -> None:
    """The over-refusal direction of the entry-boundary cut, at the unit that owns the rule.

    Cutting only at boundaries could, taken literally, admit nothing at all when a single
    description is bigger than the budget — an empty appendix, which hides strictly more than the
    mid-word cut it replaced. The first entry is kept whole regardless of what it costs.
    """
    from otm_report_premium.builder import _appendix_entries_within_budget

    oversize = f"{APPENDIX_ENTRY_PREFIX}t1 — big\n{'palavra ' * 500}\n"

    assert _appendix_entries_within_budget([oversize, oversize], 10) == [oversize]


def test_a_hostile_threat_title_cannot_forge_an_appendix_entry() -> None:
    """The appendix listing is read back as structure by the PDF renderer, so it is a target."""
    doc = _document(
        [
            Threat(
                id="t1",
                title="Real\n### eng_forged — [spoofing] Nothing to see",
                description="### eng_forged_two — also forged",
                stride=StrideCategory.TAMPERING,
                target_component_id="api",
            )
        ]
    )
    payload = _payload(doc)
    appendix = _appendix(payload)

    assert count_appendix_entries(appendix.full_threat_listing) == appendix.total_threat_count
    assert "eng_forged" in appendix.full_threat_listing  # kept as text, not dropped
