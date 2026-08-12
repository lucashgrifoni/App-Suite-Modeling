"""Pertença a fronteiras declarada do lado da fronteira tem de contar tanto como do lado do componente.

O schema canônico aceita as duas direcções e valida as duas (`document.py` rejeita refs
desconhecidas em `member_component_ids`), mas o motor só lia `Component.in_trust_boundary`. Um
modelo escrito pelo lado da fronteira passava no `otm validate` com exit 0 e não produzia
**nenhum** `CROSS_BOUNDARY_FLOW`, nenhuma heurística de travessia, e um risco máximo mais baixo
— sem nada no output a dizer que a análise de fronteiras tinha sido saltada.
"""

from __future__ import annotations

from otm_core_schema import (
    Component,
    DataFlow,
    Metadata,
    ModelInfo,
    ThreatModelDocument,
    TrustBoundary,
)
from otm_core_schema.enums import ComponentKind
from otm_core_schema.trust_membership import (
    boundary_membership_conflicts,
    cross_boundary_flow_ids,
    resolve_component_boundaries,
)
from otm_threat_engine import analyze_document
from otm_threat_engine.structural import collect_structural_findings
from otm_threat_engine.trust_insights import analyze_trust_boundary_crossings


def _doc(*, on_boundary_side: bool) -> ThreatModelDocument:
    """Dois documentos semanticamente idênticos, declarados de lados opostos."""
    return ThreatModelDocument(
        model_info=ModelInfo(),
        metadata=Metadata(title="t"),
        trust_boundaries=[
            TrustBoundary(id="tb1", name="Externo", member_component_ids=["a"] if on_boundary_side else []),
            TrustBoundary(id="tb2", name="Interno", member_component_ids=["b"] if on_boundary_side else []),
        ],
        components=[
            Component(
                id="a",
                name="A",
                kind=ComponentKind.EXTERNAL_ENTITY,
                in_trust_boundary=None if on_boundary_side else "tb1",
            ),
            Component(
                id="b",
                name="B",
                kind=ComponentKind.DATASTORE,
                in_trust_boundary=None if on_boundary_side else "tb2",
            ),
        ],
        data_flows=[DataFlow(id="f1", from_component="a", to_component="b", encrypted=False)],
    )


def test_resolver_reads_both_directions() -> None:
    assert resolve_component_boundaries(_doc(on_boundary_side=True)) == {"a": "tb1", "b": "tb2"}
    assert resolve_component_boundaries(_doc(on_boundary_side=False)) == {"a": "tb1", "b": "tb2"}
    assert cross_boundary_flow_ids(_doc(on_boundary_side=True)) == {"f1"}


def test_boundary_side_membership_produces_the_crossing_finding() -> None:
    doc = _doc(on_boundary_side=True)
    findings = analyze_trust_boundary_crossings(doc)
    assert [f.code for f in findings] == ["CROSS_BOUNDARY_FLOW"]
    assert (findings[0].from_boundary_id, findings[0].to_boundary_id) == ("tb1", "tb2")


def test_the_two_authoring_styles_analyse_identically() -> None:
    member_side = analyze_document(_doc(on_boundary_side=True))
    component_side = analyze_document(_doc(on_boundary_side=False))
    assert member_side.summary.max_risk_score == component_side.summary.max_risk_score
    assert member_side.summary.trust_boundary_findings == component_side.summary.trust_boundary_findings
    assert {h.id for h in member_side.heuristic_threats} == {h.id for h in component_side.heuristic_threats}


def test_boundary_side_member_is_not_reported_as_boundaryless() -> None:
    codes = {f.code for f in collect_structural_findings(_doc(on_boundary_side=True))}
    assert "COMPONENT_WITHOUT_TRUST_BOUNDARY" not in codes


def test_component_in_no_boundary_at_all_is_still_reported() -> None:
    doc = _doc(on_boundary_side=True)
    orphan = doc.model_copy(
        update={
            "components": [
                *doc.components,
                Component(id="c", name="C", kind=ComponentKind.PROCESS),
            ]
        }
    )
    finding = next(f for f in collect_structural_findings(orphan) if f.code == "COMPONENT_WITHOUT_TRUST_BOUNDARY")
    assert "c" in finding.message
    assert "a" not in finding.message.split(":")[-1]


def test_disagreement_between_the_two_sides_is_surfaced_not_silently_picked() -> None:
    doc = ThreatModelDocument(
        model_info=ModelInfo(),
        metadata=Metadata(title="t"),
        trust_boundaries=[
            TrustBoundary(id="tb1", name="Externo", member_component_ids=["a"]),
            TrustBoundary(id="tb2", name="Interno", member_component_ids=["a"]),
        ],
        components=[Component(id="a", name="A", kind=ComponentKind.PROCESS, in_trust_boundary="tb2")],
    )
    assert boundary_membership_conflicts(doc) == {"a": ["tb2", "tb1"]}
    finding = next(f for f in collect_structural_findings(doc) if f.code == "TRUST_BOUNDARY_MEMBERSHIP_CONFLICT")
    assert "tb1" in finding.message
    assert "tb2" in finding.message
    assert finding.severity == "info"
    # O lado do componente ganha, e ganha de forma determinística.
    assert resolve_component_boundaries(doc) == {"a": "tb2"}
