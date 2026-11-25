"""P3 security regression — a `biz_*` finding may only silence the target it points at.

STRIDE noise suppression marks a generic `eng_*` finding as covered when a specific `biz_*`
finding already describes the same root cause. It matched on a token blob built from the
threat's id, title and target ids, and each family was armed by the mere *presence* of a
`biz_*` finding anywhere in the model. The vocabulary is ordinary commerce — `billing`,
`subscription`, `ledger`, `cancel`, `webhook`, `coupon`, `payment_gateway` — so an entity whose
name merely contained one of those words lost its tampering and elevation-of-privilege findings
to a business finding on the far side of the system.

`skipped_as_duplicate` is not a label. It is a hard exclusion filter in `analysis_sarif`,
`analysis_diff` (and therefore the CI drift gate), `report-premium`, `risk_aggregate` and the
remediation backlog. The measured effect was a CRITICAL (25) finding on a public, unauthenticated,
boundary-crossing flow disappearing from all of them, with `otm diff --fail-on critical` exiting
0 — while the same flow renamed from `billing_admin_sync` to `partner_admin_sync`, identical in
every security property, exited 3.

Phase 1 fixed exactly this for the `authorization` family by requiring a shared target. The
other five branches kept the global match; this pins the whole family.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml
from otm_cli.cli import app
from otm_core_schema import ThreatModelDocument, ThreatModelMethodology, load_document_from_yaml_path
from otm_threat_engine import analyze_document
from otm_threat_engine.result import AnalysisResult
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_ECOMMERCE = _ROOT / "examples" / "test-apps" / "ecommerce-subscription.otm.yaml"
_GATE_TRIP = 3

_BASE: dict[str, Any] = {
    "model": {"schema_version": "1.0.0", "system_type": "web_application"},
    "metadata": {"title": "Payments", "owner": "appsec@empresa.example"},
    "trust_boundaries": [
        {"id": "internet", "name": "Internet", "member_component_ids": ["edge_gw"]},
        {
            "id": "vpc",
            "name": "VPC",
            "member_component_ids": ["payment_api", "entitlement_service", "dwh"],
        },
    ],
    "components": [
        {"id": "edge_gw", "name": "Edge gateway", "kind": "process"},
        {"id": "payment_api", "name": "Payment API", "kind": "process"},
        {"id": "entitlement_service", "name": "Entitlement service", "kind": "process"},
        {"id": "dwh", "name": "Warehouse", "kind": "datastore"},
    ],
    "data_flows": [
        {
            "id": "checkout_in",
            "name": "Checkout",
            "from_component": "edge_gw",
            "to_component": "payment_api",
            "protocol": "https",
            "authenticated": True,
            "encrypted": True,
        }
    ],
    "assets": [],
    "threats": [],
}


def _payload_with_admin_flow(flow_id: str) -> dict[str, Any]:
    """The base model plus one public, unauthenticated, privileged flow into the warehouse.

    `entitlement_service` makes `biz_payment_entitlement_mismatch` fire on a component this
    flow never touches. Only the flow id differs between the two variants.
    """
    payload = copy.deepcopy(_BASE)
    payload["data_flows"].append(
        {
            "id": flow_id,
            "name": "Admin sync",
            "from_component": "edge_gw",
            "to_component": "dwh",
            "protocol": "https",
            "authenticated": False,
            "encrypted": True,
            "auth_required": False,
            "public_exposure": True,
            "stores_sensitive_data": True,
            "affects_privileged_state": True,
        }
    )
    return payload


def _analysis(flow_id: str) -> AnalysisResult:
    return analyze_document(ThreatModelDocument.model_validate(_payload_with_admin_flow(flow_id)))


def _active_ids(result: AnalysisResult, flow_id: str) -> set[str]:
    return {h.id.replace(flow_id, "FLOW") for h in result.heuristic_threats if not h.skipped_as_duplicate}


@pytest.fixture
def ecommerce() -> AnalysisResult:
    doc = load_document_from_yaml_path(_ECOMMERCE)
    return analyze_document(doc, methodology=ThreatModelMethodology.STRIDE)


# ---------------------------------------- a business finding does not speak for other targets


def test_a_business_family_does_not_suppress_a_different_target() -> None:
    """`biz_payment_entitlement_mismatch` fires on `entitlement_service`, not on this flow."""
    tampering = next(
        h
        for h in _analysis("billing_admin_sync").heuristic_threats
        if h.id.endswith("_tampering") and h.target_data_flow_id == "billing_admin_sync"
    )

    assert tampering.skipped_as_duplicate is False
    assert tampering.risk.score == 25.0


def test_renaming_the_flow_no_longer_changes_the_analysis() -> None:
    """The A/B that made the defect undeniable: one word, two different threat sets."""
    with_keyword = _analysis("billing_admin_sync")
    without_keyword = _analysis("partner_admin_sync")

    assert _active_ids(with_keyword, "billing_admin_sync") == _active_ids(without_keyword, "partner_admin_sync")


def test_renaming_the_flow_no_longer_changes_the_gate_verdict(tmp_path: Path) -> None:
    runner = CliRunner()
    base = tmp_path / "base.otm.yaml"
    base.write_text(yaml.safe_dump(_BASE, allow_unicode=True, sort_keys=False), encoding="utf-8")
    verdicts = []
    for flow_id in ("billing_admin_sync", "partner_admin_sync"):
        head = tmp_path / f"head_{flow_id}.otm.yaml"
        head.write_text(
            yaml.safe_dump(_payload_with_admin_flow(flow_id), allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
        verdicts.append(
            runner.invoke(app, ["diff", str(base), str(head), "--with-analysis", "--fail-on", "critical"]).exit_code
        )

    assert verdicts == [_GATE_TRIP, _GATE_TRIP]


def test_the_shipped_ecommerce_model_keeps_its_payment_gateway_finding(ecommerce: AnalysisResult) -> None:
    """A real loss on a shipped example, not a synthetic one.

    The `webhook` family fires on `checkout_service` and the flow `gateway_webhook`. It used to
    also delete this HIGH (12) tampering finding on the separate `payment_gateway` component,
    because the token list carries the literal string `payment_gateway`.
    """
    by_id = {h.id: h for h in ecommerce.heuristic_threats}

    assert by_id["eng_payment_gateway_tampering"].skipped_as_duplicate is False
    assert by_id["eng_payment_gateway_tampering"].risk.score == 12.0


# ------------------------------------------------ but same-target suppression still happens


@pytest.mark.parametrize(
    "threat_id",
    [
        "eng_subscription_service_tampering",
        "eng_subscription_service_elevation_of_privilege",
        "eng_coupon_store_tampering",
        "eng_flow_gateway_webhook_tampering",
    ],
)
def test_same_target_noise_is_still_suppressed(ecommerce: AnalysisResult, threat_id: str) -> None:
    """The feature must survive its own fix: these share a target with their `biz_*` finding."""
    by_id = {h.id: h for h in ecommerce.heuristic_threats}

    assert by_id[threat_id].skipped_as_duplicate is True


def test_the_business_findings_themselves_are_never_suppressed(ecommerce: AnalysisResult) -> None:
    biz = [h for h in ecommerce.heuristic_threats if h.id.startswith("biz_")]

    assert biz
    assert not any(h.skipped_as_duplicate for h in biz)
