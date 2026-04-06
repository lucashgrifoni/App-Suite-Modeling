"""Contratos de avisos estruturais (além da validação Pydantic do documento)."""

from otm_core_schema import (
    Component,
    DataFlow,
    Metadata,
    ModelInfo,
    ThreatModelDocument,
    TrustBoundary,
)
from otm_core_schema.enums import ComponentKind
from otm_threat_engine.structural import collect_structural_findings


def test_empty_components_finding() -> None:
    doc = ThreatModelDocument(
        model_info=ModelInfo(),
        metadata=Metadata(title="x"),
        components=[],
    )
    out = collect_structural_findings(doc)
    codes = {f.code for f in out}
    assert "EMPTY_COMPONENTS" in codes
    assert any(f.severity == "warning" for f in out if f.code == "EMPTY_COMPONENTS")


def test_no_data_flows_when_multiple_components() -> None:
    doc = ThreatModelDocument(
        model_info=ModelInfo(),
        metadata=Metadata(title="x"),
        components=[
            Component(id="a", name="A", kind=ComponentKind.PROCESS),
            Component(id="b", name="B", kind=ComponentKind.PROCESS),
        ],
        data_flows=[],
    )
    out = collect_structural_findings(doc)
    assert any(f.code == "NO_DATA_FLOWS" for f in out)


def test_component_without_trust_boundary_message_lists_ids() -> None:
    doc = ThreatModelDocument(
        model_info=ModelInfo(),
        metadata=Metadata(title="x"),
        trust_boundaries=[TrustBoundary(id="tb1", name="TB", member_component_ids=[])],
        components=[
            Component(id="c1", name="One", kind=ComponentKind.PROCESS, in_trust_boundary=None),
            Component(id="c2", name="Two", kind=ComponentKind.PROCESS, in_trust_boundary="tb1"),
        ],
        data_flows=[
            DataFlow(id="f1", from_component="c1", to_component="c2"),
        ],
    )
    out = collect_structural_findings(doc)
    comp_missing = [f for f in out if f.code == "COMPONENT_WITHOUT_TRUST_BOUNDARY"]
    assert comp_missing
    assert "c1" in comp_missing[0].message
    assert "c2" not in comp_missing[0].message


def test_component_without_trust_boundary_truncates_after_ten() -> None:
    comps = [Component(id=f"c{i}", name=f"C{i}", kind=ComponentKind.PROCESS, in_trust_boundary=None) for i in range(12)]
    doc = ThreatModelDocument(
        model_info=ModelInfo(),
        metadata=Metadata(title="x"),
        trust_boundaries=[TrustBoundary(id="tb1", name="TB", member_component_ids=[])],
        components=comps,
        data_flows=[DataFlow(id="f1", from_component="c0", to_component="c1")],
    )
    out = collect_structural_findings(doc)
    msg = next(f.message for f in out if f.code == "COMPONENT_WITHOUT_TRUST_BOUNDARY")
    assert msg.endswith("…")
    assert "c9" in msg
    assert "c10" not in msg


def test_minimal_example_has_no_structural_warnings() -> None:
    from pathlib import Path

    from otm_core_schema import load_document_from_yaml_path

    doc = load_document_from_yaml_path(Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml")
    assert collect_structural_findings(doc) == []
