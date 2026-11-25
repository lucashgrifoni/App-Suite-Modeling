"""Coverage for the defensive branches the Phase 3 hardening added.

Both are error paths, which is exactly the kind of code that ships untested and then
misbehaves on the one day it runs. Neither needs a contrived call into a private helper:
the recursion guard is reached through the public rules loader, and every `_subject_of`
branch is reached through the public injectivity check.
"""

from __future__ import annotations

import pytest
from otm_core_schema import StrideCategory
from otm_threat_engine.custom_rules.loader import load_custom_rules
from otm_threat_engine.result import HeuristicThreat, assert_threat_ids_are_injective
from otm_threat_engine.risk_calc import build_risk_assessment


def _threat(threat_id: str, **target: str) -> HeuristicThreat:
    return HeuristicThreat(
        id=threat_id,
        title="t",
        description="d",
        stride=StrideCategory.TAMPERING,
        risk=build_risk_assessment(3, 3),
        **target,
    )


def test_a_deeply_nested_rules_file_is_refused_by_the_depth_ceiling(tmp_path) -> None:
    """The first line of defence: a declared ceiling, refused before the parser recurses."""
    rules = tmp_path / "deep.yaml"
    rules.write_text("[" * 60_000 + "]" * 60_000, encoding="utf-8")

    with pytest.raises(ValueError, match="YAML nesting exceeds"):
        load_custom_rules(rules)


def test_the_recursion_guard_still_catches_what_the_ceiling_lets_through(tmp_path, monkeypatch) -> None:
    """The depth ceiling is operator-overridable, so the RecursionError handler is reachable.

    `OTM_MAX_DOCUMENT_DEPTH` exists so a legitimately deep document can be accepted. Raise it
    far enough and PyYAML exhausts the interpreter stack instead — and a `RecursionError` is
    not a `YAMLError`, so without its own handler it escapes as a raw traceback rather than
    the CLI's structured error. This is the branch that turns that into a readable refusal.
    """
    monkeypatch.setenv("OTM_MAX_DOCUMENT_DEPTH", "10000000")
    rules = tmp_path / "deep.yaml"
    rules.write_text("[" * 60_000 + "]" * 60_000, encoding="utf-8")

    with pytest.raises(ValueError, match="too deeply nested"):
        load_custom_rules(rules)


def test_two_flows_claiming_one_threat_id_name_both_flows() -> None:
    collision = [
        _threat("eng_x_tampering", target_data_flow_id="a"),
        _threat("eng_x_tampering", target_data_flow_id="b"),
    ]

    with pytest.raises(ValueError, match="data flow `a`"):
        assert_threat_ids_are_injective(collision)


def test_two_assets_claiming_one_threat_id_name_both_assets() -> None:
    collision = [
        _threat("eng_x_tampering", target_asset_id="a"),
        _threat("eng_x_tampering", target_asset_id="b"),
    ]

    with pytest.raises(ValueError, match="asset `a`"):
        assert_threat_ids_are_injective(collision)


def test_an_untargeted_threat_is_described_as_the_model_as_a_whole() -> None:
    """Model-level threats (the PASTA lens emits these) carry no target at all."""
    collision = [_threat("eng_x_tampering"), _threat("eng_x_tampering")]

    with pytest.raises(ValueError, match="the model as a whole"):
        assert_threat_ids_are_injective(collision)


def test_distinct_ids_across_every_subject_kind_are_accepted() -> None:
    """The guard must not start refusing legitimate models — it only rejects collisions."""
    distinct = [
        _threat("eng_a_tampering", target_component_id="a"),
        _threat("eng_flow_b_tampering", target_data_flow_id="b"),
        _threat("eng_asset_c_tampering", target_asset_id="c"),
        _threat("eng_model_tampering"),
    ]

    assert_threat_ids_are_injective(distinct)
