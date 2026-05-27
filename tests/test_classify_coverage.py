"""Coverage — remediation classify_threat root-cause/control mapping branches."""

from __future__ import annotations

from typing import Any

from otm_core_schema import StrideCategory, ThreatModelMethodology, create_blank_document
from otm_core_schema.document import Component, FrameworkRef
from otm_core_schema.enums import ComponentKind
from otm_threat_engine.remediation.classify import (
    classify_threat,
    effort_for_threat,
    impact_level_from_risk,
)
from otm_threat_engine.result import HeuristicThreat
from otm_threat_engine.risk_calc import build_risk_assessment


def _threat(stride: StrideCategory, **extra: Any) -> HeuristicThreat:
    return HeuristicThreat(
        id="t1", title="t", description="d", stride=stride, risk=build_risk_assessment(4, 4), **extra
    )


def _doc_with_external() -> Any:
    doc = create_blank_document()
    ext = Component(id="ext1", name="Vendor", kind=ComponentKind.EXTERNAL_ENTITY)
    return doc.model_copy(update={"components": [ext]})


def test_classify_all_stride_roots() -> None:
    doc = create_blank_document()
    for st in StrideCategory:
        root, ctrl, cat, _layer = classify_threat(_threat(st), doc, ThreatModelMethodology.STRIDE)
        assert root and ctrl and cat


def test_classify_third_party_trust() -> None:
    doc = _doc_with_external()
    t = _threat(
        StrideCategory.SPOOFING,
        target_component_id="ext1",
        framework_refs=[FrameworkRef(framework="NIST supplier governance", control_id="SR-1")],
    )
    root, ctrl, cat, layer = classify_threat(t, doc, ThreatModelMethodology.STRIDE)
    assert root == "third_party_trust"
    assert cat == "third_party_integration"
    assert layer == "edge"  # external entity -> edge layer


def test_classify_ai_context_via_plot4ai() -> None:
    doc = create_blank_document()
    root, ctrl, cat, _ = classify_threat(
        _threat(StrideCategory.INFORMATION_DISCLOSURE), doc, ThreatModelMethodology.PLOT4AI
    )
    assert cat == "ai_ml_specific"
    assert ctrl.startswith("ai_ml")


def test_classify_ai_context_via_keywords() -> None:
    doc = create_blank_document()
    t = HeuristicThreat(
        id="t2", title="LLM prompt injection", description="rag inference risk",
        stride=StrideCategory.TAMPERING, risk=build_risk_assessment(3, 3),
    )
    _root, _ctrl, cat, _ = classify_threat(t, doc, ThreatModelMethodology.STRIDE)
    assert cat == "ai_ml_specific"


def test_effort_and_impact_helpers() -> None:
    low = _threat(StrideCategory.REPUDIATION)
    assert effort_for_threat(low, "non_repudiation_and_audit") in {"low", "medium", "high"}
    high = HeuristicThreat(
        id="t3", title="x", description="d", stride=StrideCategory.ELEVATION_OF_PRIVILEGE,
        risk=build_risk_assessment(5, 5),
    )
    assert effort_for_threat(high, "identity_and_authorization_gaps") in {"high", "medium"}
    assert impact_level_from_risk(high) in {"low", "medium", "high", "critical"}
