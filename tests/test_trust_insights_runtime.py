from otm_core_schema import DataFlow, Metadata, ThreatModelDocument, TrustBoundary
from otm_core_schema.document import Component
from otm_core_schema.enums import ComponentKind
from otm_threat_engine.trust_insights import analyze_trust_boundary_crossings


def test_analyze_trust_boundary_crossings_emits_stable_code_and_flow_id() -> None:
    doc = ThreatModelDocument(
        metadata=Metadata(title="x"),
        components=[
            Component(
                id="a",
                name="A",
                kind=ComponentKind.PROCESS,
                in_trust_boundary="tb1",
            ),
            Component(
                id="b",
                name="B",
                kind=ComponentKind.PROCESS,
                in_trust_boundary="tb2",
            ),
        ],
        trust_boundaries=[
            TrustBoundary(id="tb1", name="TB 1", member_component_ids=["a"]),
            TrustBoundary(id="tb2", name="TB 2", member_component_ids=["b"]),
        ],
        data_flows=[
            DataFlow(
                id="f1",
                name="flow",
                from_component="a",
                to_component="b",
            )
        ],
    )
    findings = analyze_trust_boundary_crossings(doc)
    assert findings
    f = findings[0]
    assert f.code == "CROSS_BOUNDARY_FLOW"
    assert f.data_flow_id == "f1"
    assert "f1" in f.message


def test_analyze_trust_boundary_crossings_skips_when_boundary_missing() -> None:
    doc = ThreatModelDocument(
        metadata=Metadata(title="x"),
        components=[
            Component(
                id="a",
                name="A",
                kind=ComponentKind.PROCESS,
                in_trust_boundary=None,
            ),
            Component(
                id="b",
                name="B",
                kind=ComponentKind.PROCESS,
                in_trust_boundary="tb2",
            ),
        ],
        trust_boundaries=[TrustBoundary(id="tb2", name="TB 2", member_component_ids=["b"])],
        data_flows=[DataFlow(id="f1", from_component="a", to_component="b")],
    )
    findings = analyze_trust_boundary_crossings(doc)
    assert findings == []
