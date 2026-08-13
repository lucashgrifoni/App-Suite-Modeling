"""Round-5: the Markdown analysis report must say which view it is and what it withheld.

On `examples/test-apps/ecommerce-subscription.otm.yaml` the engine produces 48 heuristic threats
and flags 9 `skipped_as_duplicate`. The report showed 39 and:

* printed the identical heading `### Ameaças sugeridas (harmonizadas)` in **all four** toggle
  combinations, including `OTM_MARKDOWN_VIEW_MODE=legacy`, which renders the complete, unreduced
  list — a reader holding the file could not tell which of the two views they had;
* never stated how many findings the engine had withheld, so reconciling the report against
  `otm analyze --json-out` left nine findings unaccounted for;
* offered `legacy`, whose own docstring promised "sem supressão (apresenta tudo)", while the nine
  had already been dropped upstream and no exporter setting could bring them back.

The counts themselves were accurate — "39 active threats" is a true statement about active
threats — so what is fixed is the labelling and the disclosure, not the arithmetic.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from otm_core_schema import load_document_from_yaml_path
from otm_exporters import export_analysis_markdown
from otm_exporters.analysis_markdown import _markdown_view_mode
from otm_threat_engine import AnalysisResult, analyze_document

_ROOT = Path(__file__).resolve().parents[1]
_DEDUPING_MODEL = _ROOT / "examples" / "test-apps" / "ecommerce-subscription.otm.yaml"
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"

_HEADINGS = re.compile(r"^### (?:Ameaças sugeridas|Suggested threats) .*$", re.MULTILINE)


@pytest.fixture(scope="module")
def deduping() -> AnalysisResult:
    return analyze_document(load_document_from_yaml_path(_DEDUPING_MODEL))


@pytest.fixture(scope="module")
def clean() -> AnalysisResult:
    return analyze_document(load_document_from_yaml_path(_MINIMAL))


def _withheld(result: AnalysisResult) -> int:
    return sum(1 for t in result.heuristic_threats if t.skipped_as_duplicate)


def test_the_fixture_model_really_does_deduplicate(deduping: AnalysisResult) -> None:
    """Premise of everything below."""
    assert _withheld(deduping) > 0


def test_the_report_states_how_many_findings_were_withheld(deduping: AnalysisResult) -> None:
    markdown = export_analysis_markdown(deduping)

    assert f"De-duplicação do motor:** {_withheld(deduping)} " in markdown


def test_the_english_report_states_it_too(deduping: AnalysisResult) -> None:
    markdown = export_analysis_markdown(deduping, locale="en")

    assert f"Engine de-duplication:** {_withheld(deduping)} " in markdown


def test_a_report_with_nothing_withheld_stays_quiet(clean: AnalysisResult) -> None:
    """The over-disclosure direction: no note where there is nothing to note."""
    assert _withheld(clean) == 0  # fixture premise
    markdown = export_analysis_markdown(clean)

    assert "De-duplicação do motor" not in markdown


def test_the_note_points_at_the_artifact_that_still_has_them(deduping: AnalysisResult) -> None:
    markdown = export_analysis_markdown(deduping)

    assert "skipped_as_duplicate" in markdown


@pytest.mark.parametrize("locale", ["pt-BR", "en"])
def test_the_two_views_no_longer_share_one_heading(
    deduping: AnalysisResult, locale: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OTM_MARKDOWN_VIEW_MODE", "harmonized")
    harmonized = _HEADINGS.findall(export_analysis_markdown(deduping, locale=locale))
    monkeypatch.setenv("OTM_MARKDOWN_VIEW_MODE", "legacy")
    complete = _HEADINGS.findall(export_analysis_markdown(deduping, locale=locale))

    assert harmonized and complete
    assert harmonized != complete


def test_the_complete_view_is_not_called_harmonized(deduping: AnalysisResult, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_MARKDOWN_VIEW_MODE", "legacy")

    markdown = export_analysis_markdown(deduping)

    assert "(harmonizadas)" not in markdown
    assert "(lista completa)" in markdown


def test_the_harmonized_view_keeps_its_own_label(deduping: AnalysisResult, monkeypatch: pytest.MonkeyPatch) -> None:
    """The default view must not have been relabelled by the fix."""
    monkeypatch.setenv("OTM_MARKDOWN_VIEW_MODE", "harmonized")

    markdown = export_analysis_markdown(deduping)

    assert "(harmonizadas)" in markdown
    assert "(lista completa)" not in markdown


def test_the_complete_view_really_carries_more_entries(
    deduping: AnalysisResult, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The heading now makes a claim about the content; the content has to back it."""
    monkeypatch.setenv("OTM_MARKDOWN_VIEW_MODE", "harmonized")
    harmonized = export_analysis_markdown(deduping).count("` → ")
    monkeypatch.setenv("OTM_MARKDOWN_VIEW_MODE", "legacy")
    complete = export_analysis_markdown(deduping).count("` → ")

    assert complete >= harmonized


@pytest.mark.parametrize("value", ["", "garbage", "LEGACY", "harmonized"])
def test_an_unknown_view_mode_still_falls_back_to_harmonized(value: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Unchanged behaviour, pinned because the heading now depends on it."""
    monkeypatch.setenv("OTM_MARKDOWN_VIEW_MODE", value)

    assert _markdown_view_mode() == ("legacy" if value.strip().lower() == "legacy" else "harmonized")
