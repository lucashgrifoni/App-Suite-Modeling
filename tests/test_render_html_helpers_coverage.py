"""Coverage — render_html pure helper functions (bands, badges, emoji, headings)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
from otm_report_premium import render_html as rh  # noqa: E402


def test_severity_band_all() -> None:
    assert rh._severity_band(None)[0] == "—"
    assert rh._severity_band(25)[0] == "Critical"
    assert rh._severity_band(16)[0] == "High"
    assert rh._severity_band(10)[0] == "Medium"
    assert rh._severity_band(2)[0] == "Low"


def test_tier_badge_class() -> None:
    assert rh._tier_badge_class("P1") == "bg-p1"
    assert rh._tier_badge_class("P2") == "bg-p2"
    assert rh._tier_badge_class("P3") == "bg-p3"
    assert rh._tier_badge_class("other") == "bg-p3"


def test_root_cause_row_class_cycles() -> None:
    assert rh._root_cause_row_class(0) == "rc-p1"
    assert rh._root_cause_row_class(5) == "rc-p2"
    assert rh._root_cause_row_class(3) == "rc-p4"


def test_status_emoji_all() -> None:
    assert rh._status_emoji("requires_immediate_attention")
    assert rh._status_emoji("action_recommended")
    assert rh._status_emoji("acceptable_with_follow_up")


@pytest.mark.parametrize("phase", ["immediate", "short", "medium"])
def test_roadmap_heading_phases(phase: str) -> None:
    assert isinstance(rh._roadmap_heading(phase), str)  # type: ignore[arg-type]


def test_esc_quotes() -> None:
    assert "&quot;" in rh._esc('a"b') or "&#x27;" in rh._esc("a'b") or rh._esc("<x>") == "&lt;x&gt;"
