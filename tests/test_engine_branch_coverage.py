"""Coverage — specific real branches in engine helpers (confidence bump, PLOT4ai textual marker)."""

from __future__ import annotations

from otm_core_schema import create_blank_document
from otm_threat_engine.anti_pattern_library import _bump_confidence
from otm_threat_engine.methodology_lenses.recommendation import _plot4ai_recommendation_detail


def test_bump_confidence_structural_primary_promotes() -> None:
    assert _bump_confidence("low", "structural_primary") == "medium"
    assert _bump_confidence("medium", "structural_primary") == "high"
    assert _bump_confidence("high", "structural_primary") == "high"  # already top, unchanged


def test_bump_confidence_unknown_hint_passes_through() -> None:
    # hint outside the ordered scale is returned verbatim (defensive guard branch)
    assert _bump_confidence("weird", "structural_primary") == "weird"


def test_bump_confidence_non_structural_reason_unchanged() -> None:
    assert _bump_confidence("low", "corpus_secondary") == "low"


def test_plot4ai_detail_via_safe_ai_marker_branch() -> None:
    # No AI tags, but text carries the short `ai` token plus a technical companion term ->
    # exercises the `elif has_safe_ai_marker(text)` branch.
    doc = create_blank_document()
    result = _plot4ai_recommendation_detail(doc, "ai inference")
    assert result is not None
    reason, evidence = result
    assert "sinal técnico de IA" in reason
    assert any("Token AI" in e for e in evidence)


def test_plot4ai_detail_returns_none_without_signal() -> None:
    doc = create_blank_document()
    assert _plot4ai_recommendation_detail(doc, "plain ordering system with no ai") is None
