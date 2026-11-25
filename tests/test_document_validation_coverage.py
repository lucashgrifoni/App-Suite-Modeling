"""Coverage — ThreatModelDocument cross-reference validation raises."""

from __future__ import annotations

import copy
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from pydantic import ValidationError

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def _base() -> dict[str, Any]:
    d = load_document_from_yaml_path(_MINIMAL).model_dump(mode="python", by_alias=True)
    # ensure optional sections exist so we can inject dangling refs
    d.setdefault("assets", [])
    d.setdefault("trust_boundaries", d.get("trust_boundaries") or [])
    d.setdefault("threats", [])
    d.setdefault("mitigations", [])
    d.setdefault("evidence_suggestions", [])
    return d


def _comp_id(d: dict[str, Any]) -> str:
    return d["components"][0]["id"]


def _mutators() -> dict[str, Callable[[dict[str, Any]], None]]:
    def dup_component(d: dict[str, Any]) -> None:
        d["components"].append(copy.deepcopy(d["components"][0]))

    def bad_component_boundary(d: dict[str, Any]) -> None:
        d["components"][0]["in_trust_boundary"] = "ghost_tb"

    def bad_component_asset(d: dict[str, Any]) -> None:
        d["components"][0]["asset_ids"] = ["ghost_asset"]

    def bad_asset_component(d: dict[str, Any]) -> None:
        d["assets"].append({"id": "a_x", "name": "A", "related_component_ids": ["ghost_comp"]})

    def bad_asset_flow(d: dict[str, Any]) -> None:
        d["assets"].append({"id": "a_y", "name": "A", "related_data_flow_ids": ["ghost_flow"]})

    def bad_tb_member(d: dict[str, Any]) -> None:
        d["trust_boundaries"][0]["member_component_ids"] = ["ghost_comp"]

    def bad_tb_crossing(d: dict[str, Any]) -> None:
        d["trust_boundaries"][0]["crossing_flow_ids"] = ["ghost_flow"]

    def bad_tb_outside(d: dict[str, Any]) -> None:
        d["trust_boundaries"][0]["outside_component_ids"] = ["ghost_comp"]

    def bad_threat_target(d: dict[str, Any]) -> None:
        d["threats"].append({"id": "t_x", "title": "T", "stride": "tampering", "target_component_id": "ghost_comp"})

    def bad_threat_flow(d: dict[str, Any]) -> None:
        d["threats"].append({"id": "t_f", "title": "T", "stride": "tampering", "target_data_flow_id": "ghost_flow"})

    def bad_threat_asset(d: dict[str, Any]) -> None:
        d["threats"].append({"id": "t_a", "title": "T", "stride": "tampering", "target_asset_id": "ghost_asset"})

    def bad_threat_evidence(d: dict[str, Any]) -> None:
        d["threats"].append({"id": "t_e", "title": "T", "stride": "tampering", "evidence_suggestion_ids": ["ghost_ev"]})

    def bad_mitigation_threat(d: dict[str, Any]) -> None:
        d["mitigations"].append({"id": "m_x", "title": "M", "threat_ids": ["ghost_threat"]})

    def bad_evidence_threat(d: dict[str, Any]) -> None:
        d["evidence_suggestions"].append({"id": "e_x", "title": "E", "related_threat_ids": ["ghost_threat"]})

    return {
        "dup_component": dup_component,
        "bad_component_boundary": bad_component_boundary,
        "bad_component_asset": bad_component_asset,
        "bad_asset_component": bad_asset_component,
        "bad_asset_flow": bad_asset_flow,
        "bad_tb_member": bad_tb_member,
        "bad_tb_crossing": bad_tb_crossing,
        "bad_tb_outside": bad_tb_outside,
        "bad_threat_target": bad_threat_target,
        "bad_threat_flow": bad_threat_flow,
        "bad_threat_asset": bad_threat_asset,
        "bad_threat_evidence": bad_threat_evidence,
        "bad_mitigation_threat": bad_mitigation_threat,
        "bad_evidence_threat": bad_evidence_threat,
    }


# The message each mutation must produce. Asserting only "something raised" would pass even
# if an unrelated field blew up first, so every case pins the reference the validator names.
_EXPECTED_MESSAGE = {
    "dup_component": r"duplicate id in components",
    "bad_component_boundary": r"component 'user' references unknown trust boundary 'ghost_tb'",
    "bad_component_asset": r"component 'user' references unknown asset 'ghost_asset'",
    "bad_asset_component": r"asset 'a_x' references unknown component 'ghost_comp'",
    "bad_asset_flow": r"asset 'a_y' references unknown data_flow 'ghost_flow'",
    "bad_tb_member": r"trust_boundary 'internet' references unknown component 'ghost_comp'",
    "bad_tb_crossing": r"trust_boundary 'internet' references unknown data_flow 'ghost_flow'",
    "bad_tb_outside": r"trust_boundary 'internet' references unknown outside component 'ghost_comp'",
    "bad_threat_target": r"threat 't_x' target_component_id unknown",
    "bad_threat_flow": r"threat 't_f' target_data_flow_id unknown",
    "bad_threat_asset": r"threat 't_a' target_asset_id unknown",
    "bad_threat_evidence": r"threat 't_e' references unknown evidence_suggestion 'ghost_ev'",
    "bad_mitigation_threat": r"mitigation 'm_x' references unknown threat 'ghost_threat'",
    "bad_evidence_threat": r"evidence_suggestion 'e_x' references unknown threat 'ghost_threat'",
}


def test_every_mutator_has_an_expected_message() -> None:
    """A new mutation must not slip in with only a 'something raised' assertion."""
    assert set(_mutators()) == set(_EXPECTED_MESSAGE)


@pytest.mark.parametrize("name", list(_mutators().keys()))
def test_dangling_reference_raises(name: str) -> None:
    d = _base()
    _mutators()[name](d)
    with pytest.raises(ValidationError, match=_EXPECTED_MESSAGE[name]):
        ThreatModelDocument.model_validate(d)


def test_valid_minimal_still_validates() -> None:
    assert ThreatModelDocument.model_validate(_base()) is not None
