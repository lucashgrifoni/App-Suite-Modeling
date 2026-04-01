"""Backlog de remediação: geração, agrupamento, priorização e explainability."""

from __future__ import annotations

from otm_core_schema import (
    Component,
    ComponentKind,
    Metadata,
    ModelInfo,
    RiskAssessment,
    StrideCategory,
    ThreatModelDocument,
)
from otm_core_schema.enums import ThreatModelMethodology
from otm_threat_engine.remediation import build_remediation_backlog
from otm_threat_engine.result import (
    AnalysisResult,
    AnalysisSummary,
    HeuristicThreat,
    StructuralFinding,
    TrustBoundaryFinding,
)

ENGINE_VERSION = "test"


def _minimal_doc() -> ThreatModelDocument:
    return ThreatModelDocument(
        metadata=Metadata(title="Svc"),
        model_info=ModelInfo(
            methodology=ThreatModelMethodology.STRIDE,
        ),
        components=[
            Component(
                id="api",
                name="API",
                kind=ComponentKind.PROCESS,
            ),
        ],
    )


def _threat_li(tid: str, stride: StrideCategory, likelihood: int, impact: int) -> HeuristicThreat:
    return HeuristicThreat(
        id=tid,
        title=f"Threat {tid}",
        description="Desc",
        stride=stride,
        target_component_id="api",
        risk=RiskAssessment(likelihood=likelihood, impact=impact),
    )


def test_backlog_simple_generation() -> None:
    doc = _minimal_doc()
    t = _threat_li("h1", StrideCategory.SPOOFING, 4, 5)
    result = AnalysisResult(
        engine_version=ENGINE_VERSION,
        methodology=ThreatModelMethodology.STRIDE,
        document_title="Svc",
        heuristic_threats=[t],
        summary=AnalysisSummary(heuristic_threats_generated=1, max_risk_score=20),
    )
    bl = build_remediation_backlog(result, doc)
    assert bl.schema_version
    assert len(bl.items) == 1
    assert bl.items[0].related_findings[0].id == "h1"
    assert bl.items[0].component_labels == ["API"]
    assert bl.by_root_cause
    assert bl.items[0].explainability


def test_grouping_coherent() -> None:
    doc = _minimal_doc()
    threats = [
        _threat_li("a", StrideCategory.SPOOFING, 3, 3),
        _threat_li("b", StrideCategory.ELEVATION_OF_PRIVILEGE, 3, 4),
    ]
    result = AnalysisResult(
        engine_version=ENGINE_VERSION,
        document_title="Svc",
        heuristic_threats=threats,
        summary=AnalysisSummary(),
    )
    bl = build_remediation_backlog(result, doc)
    root = bl.items[0].grouped_root_cause
    assert all(i.grouped_root_cause == root for i in bl.items)
    assert len(bl.by_root_cause[root]) == 2


def test_priority_ordering() -> None:
    doc = _minimal_doc()
    result = AnalysisResult(
        engine_version=ENGINE_VERSION,
        document_title="Svc",
        heuristic_threats=[
            _threat_li("low", StrideCategory.INFORMATION_DISCLOSURE, 2, 2),
            _threat_li("hi", StrideCategory.SPOOFING, 5, 5),
        ],
        summary=AnalysisSummary(),
    )
    bl = build_remediation_backlog(result, doc)
    hi_item = next(i for i in bl.items if i.related_findings[0].id == "hi")
    lo_item = next(i for i in bl.items if i.related_findings[0].id == "low")
    assert hi_item.priority_rank < lo_item.priority_rank
    assert hi_item.priority_label == "urgent"
    assert hi_item.priority_explanation


def test_explainability_fields() -> None:
    doc = _minimal_doc()
    result = AnalysisResult(
        engine_version=ENGINE_VERSION,
        document_title="Svc",
        heuristic_threats=[_threat_li("x", StrideCategory.TAMPERING, 3, 3)],
        structural_findings=[
            StructuralFinding(code="S001", message="orphan flow"),
        ],
        trust_boundary_findings=[
            TrustBoundaryFinding(code="TB1", message="cross", data_flow_id="f1"),
        ],
        pack_control_hints=["Review PCI alignment"],
        summary=AnalysisSummary(),
    )
    bl = build_remediation_backlog(result, doc)
    kinds = {i.related_findings[0].kind for i in bl.items}
    assert "heuristic_threat" in kinds
    assert "structural" in kinds
    assert "trust_boundary" in kinds
    assert "pack_hint" in kinds
    for it in bl.items:
        assert it.rationale
        assert it.owner_explanation
        assert it.next_step
        assert it.explainability


def test_contract_stability_keys() -> None:
    doc = _minimal_doc()
    result = AnalysisResult(
        engine_version=ENGINE_VERSION,
        document_title="Test",
        heuristic_threats=[_threat_li("one", StrideCategory.REPUDIATION, 2, 2)],
        summary=AnalysisSummary(),
    )
    bl = build_remediation_backlog(result, doc)
    d = bl.model_dump(mode="json")
    assert "top_5_action_ids" in d
    assert "quick_win_ids" in d
    assert "synergy_notes" in d
    assert isinstance(d["items"], list)


def test_skipped_threats_ignored() -> None:
    doc = _minimal_doc()
    t = _threat_li("skip", StrideCategory.SPOOFING, 2, 2)
    t2 = t.model_copy(update={"skipped_as_duplicate": True, "id": "skip2"})
    result = AnalysisResult(
        engine_version=ENGINE_VERSION,
        document_title="Svc",
        heuristic_threats=[t, t2],
        summary=AnalysisSummary(),
    )
    bl = build_remediation_backlog(result, doc)
    ids = {
        i.related_findings[0].id
        for i in bl.items
        if i.related_findings[0].kind == "heuristic_threat"
    }
    assert "skip2" not in ids
