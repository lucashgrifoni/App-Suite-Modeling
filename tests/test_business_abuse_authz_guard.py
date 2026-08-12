"""Regression guards for the always-on `biz_authorization_*` rule.

`add_business_context_authz` used to be the only business-abuse rule with no
guard, so it fired on every document — including an empty one. That had two
consequences beyond the phantom finding itself:

1. every analysis reported a non-zero `max_risk_score` and a "high" risk
   posture from a threat with no target;
2. it pinned the `authorization` family flag permanently on, which made the
   STRIDE noise-suppression gate delete `tampering` and
   `elevation_of_privilege` findings from any component whose id or name
   merely contained "authorization" / "ownership" / "vinculo" — exactly the
   components where privilege escalation matters most.
"""

from __future__ import annotations

from otm_core_schema import load_document_from_dict
from otm_threat_engine import analyze_document

_ADMIN_PROCESS = {
    "kind": "process",
    "supports_admin_operations": True,
}


def _single_component_doc(component_id: str, name: str) -> dict:
    return {
        "metadata": {"title": f"model with {component_id}"},
        "components": [{"id": component_id, "name": name, **_ADMIN_PROCESS}],
    }


def _active_strides(result, component_id: str) -> set[str]:
    return {
        h.stride.value
        for h in result.heuristic_threats
        if h.id.startswith("eng_") and h.target_component_id == component_id and not h.skipped_as_duplicate
    }


def _suppressed_ids(result) -> list[str]:
    return [h.id for h in result.heuristic_threats if h.id.startswith("eng_") and h.skipped_as_duplicate]


def test_empty_model_produces_no_phantom_authorization_threat() -> None:
    result = analyze_document(load_document_from_dict({"metadata": {"title": "empty"}}))

    assert [h.id for h in result.heuristic_threats] == []


def test_empty_model_is_not_reported_as_high_risk() -> None:
    result = analyze_document(load_document_from_dict({"metadata": {"title": "empty"}}))

    # A model with no components cannot justify a "high" posture; that reading
    # came entirely from the ungated authorization threat scoring 3x4=12.
    assert result.decision_cockpit["risk_posture"] != "high"


def test_component_named_authorization_keeps_its_tampering_and_eop_threats() -> None:
    """Naming a component "authorization" must not delete threats from it."""
    authz = analyze_document(
        load_document_from_dict(_single_component_doc("authorization_service", "Authorization Service"))
    )
    orders = analyze_document(load_document_from_dict(_single_component_doc("orders_service", "Orders Service")))

    assert _active_strides(authz, "authorization_service") == _active_strides(orders, "orders_service")
    assert {"tampering", "elevation_of_privilege"} <= _active_strides(authz, "authorization_service")
    assert _suppressed_ids(authz) == []


def test_ownership_named_component_keeps_its_threats() -> None:
    """`ownership` is a second token the suppression branch matched on."""
    result = analyze_document(
        load_document_from_dict(_single_component_doc("ownership_registry", "Ownership Registry"))
    )

    assert {"tampering", "elevation_of_privilege"} <= _active_strides(result, "ownership_registry")
    assert _suppressed_ids(result) == []


def test_authorization_threat_still_fires_when_a_sensitive_flow_exists() -> None:
    """The rule must keep working for the models it was written for."""
    doc = load_document_from_dict(
        {
            "metadata": {"title": "checkout"},
            "components": [
                {"id": "web", "name": "Web", "kind": "process"},
                {"id": "checkout_service", "name": "Checkout Service", "kind": "process"},
            ],
            "data_flows": [
                {
                    "id": "checkout_submit",
                    "name": "Checkout submit",
                    "from_component": "web",
                    "to_component": "checkout_service",
                }
            ],
        }
    )

    result = analyze_document(doc)

    authz = [h for h in result.heuristic_threats if h.id == "biz_authorization_without_business_context"]
    assert len(authz) == 1, "the rule must still fire on a model with a sensitive flow"
    assert authz[0].target_component_id == "checkout_service"
