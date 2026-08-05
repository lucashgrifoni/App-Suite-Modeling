"""One canonical severity band, shared by every surface that labels a threat.

Regression: the engine banded `critical>=20, high>=12, medium>=6` while the premium
report banded `critical>=20, high>=15, medium>=9`. A threat scoring 12 was therefore
reported as **high** by `otm analyze` and **medium** by the premium report. No test
discriminated the two (the existing cases used 25/16/10/2, where both agree), so the
divergence survived. These tests exercise the boundaries where they disagreed.
"""

from __future__ import annotations

import pytest
from otm_report_premium.builder import _band_for_score, _risk_label, _urgency_level
from otm_report_premium.render_html import _severity_band as _html_band
from otm_report_premium.report_i18n import premium_builder_copy
from otm_threat_engine import SEVERITY_ORDER, severity_at_least, severity_for_score, severity_rank
from otm_threat_engine.risk_aggregate import _severity_bucket

# (score, expected band) — includes every boundary and the values that used to disagree.
_CASES = [
    (0, "low"),
    (1, "low"),
    (5, "low"),
    (5.9, "low"),
    (6, "medium"),  # engine medium / premium said low
    (8, "medium"),
    (9, "medium"),
    (11.9, "medium"),
    (12, "high"),  # engine high / premium said medium
    (14, "high"),
    (15, "high"),
    (19.9, "high"),
    (20, "critical"),
    (25, "critical"),
]


@pytest.mark.parametrize(("score", "expected"), _CASES)
def test_canonical_band_boundaries(score: float, expected: str) -> None:
    assert severity_for_score(score) == expected


def test_none_score_is_low() -> None:
    assert severity_for_score(None) == "low"


@pytest.mark.parametrize(("score", "expected"), _CASES)
def test_every_surface_agrees_with_the_canonical_band(score: float, expected: str) -> None:
    """Engine aggregate, premium payload, and premium HTML must all report one band."""
    assert _severity_bucket(score) == expected, "engine risk_aggregate drifted"
    assert _band_for_score(score) == expected, "premium builder drifted"
    assert _html_band(score)[0].lower() == expected, "premium HTML drifted"
    assert _html_band(score)[1] == f"sev-{expected}", "premium HTML css class drifted"


# --------------------------------------------- regression from the pre-v7.8.0 deep review
#
# The unification above was only half done: `_band_for_score` and the HTML band moved to the
# canonical cut points, but the *narrative* helpers in the same module — the cover adjective,
# the urgency level and the readiness question — kept the old 20/15/9. The result was one
# document that called the same score "medium" on its cover and "High" in its own severity
# table. The tests above could not see it: they never touched those helpers.


@pytest.mark.parametrize(("score", "expected"), _CASES)
def test_narrative_helpers_use_the_canonical_cut_points(score: float, expected: str) -> None:
    """Different vocabulary is fine. A different *ruler* is the bug."""
    b = premium_builder_copy("en")
    expected_label = {
        "critical": b.risk_elevated,
        "high": b.risk_high,
        "medium": b.risk_medium,
        "low": b.risk_low_moderate,
    }[expected]
    assert _risk_label(score, b) == expected_label, "cover/executive adjective drifted from the band"

    expected_urgency = {"critical": "high", "high": "high", "medium": "medium", "low": "low"}[expected]
    assert _urgency_level(score) == expected_urgency, "urgency level drifted from the band"


@pytest.mark.parametrize("score", [12, 14])
def test_a_high_band_score_is_not_narrated_as_medium(score: float) -> None:
    """The exact contradiction that shipped: band says high, the cover said medium."""
    b = premium_builder_copy("en")
    assert severity_for_score(score) == "high"
    assert _risk_label(score, b) == b.risk_high
    assert _urgency_level(score) == "high"


@pytest.mark.parametrize("score", [6, 8])
def test_a_medium_band_score_is_not_narrated_as_low(score: float) -> None:
    b = premium_builder_copy("en")
    assert severity_for_score(score) == "medium"
    assert _risk_label(score, b) == b.risk_medium
    assert _urgency_level(score) == "medium"


def test_severity_ordering_helpers() -> None:
    assert SEVERITY_ORDER == ("low", "medium", "high", "critical")
    assert [severity_rank(s) for s in SEVERITY_ORDER] == [0, 1, 2, 3]

    assert severity_at_least("critical", "high")
    assert severity_at_least("high", "high")
    assert not severity_at_least("medium", "high")
    assert severity_at_least("low", "low")
