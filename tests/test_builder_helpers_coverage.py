"""Coverage — premium report builder pure helpers (name lookups, score bands)."""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("fastapi")
from otm_core_schema import load_document_from_yaml_path  # noqa: E402
from otm_report_premium import builder as bd  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_name_lookups_none_found_and_missing() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    assert bd._component_name(doc, None) is None
    assert bd._asset_name(doc, None) is None
    assert bd._boundary_name(doc, None) is None
    c = doc.components[0]
    assert bd._component_name(doc, c.id) == c.name
    # unknown ids fall back to the id itself
    assert bd._component_name(doc, "ghost") == "ghost"
    assert bd._asset_name(doc, "ghost") == "ghost"
    assert bd._boundary_name(doc, "ghost") == "ghost"
    if doc.trust_boundaries:
        b = doc.trust_boundaries[0]
        assert bd._boundary_name(doc, b.id) == b.name


def test_app_version_returns_string() -> None:
    assert isinstance(bd._app_version(), str)


def test_overall_status_and_risk_label_bands() -> None:
    from otm_report_premium.report_i18n import premium_builder_copy

    b = premium_builder_copy("en")
    for score in (None, 5.0, 10.0, 13.0, 16.0, 25.0):
        status, msg = bd._overall_status(score, b)
        assert status in {
            "requires_immediate_attention",
            "action_recommended",
            "acceptable_with_follow_up",
        }
        assert isinstance(bd._risk_label(score, b), str)
