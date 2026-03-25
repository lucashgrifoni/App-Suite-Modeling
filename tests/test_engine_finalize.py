from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_core_schema.enums import ThreatModelMethodology
from otm_threat_engine.engine import ThreatAnalysisEngine
from otm_threat_engine.engine_finalize import finalize_analysis_with_methodology

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_finalize_analysis_updates_methodology_and_reason() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    engine = ThreatAnalysisEngine()
    base = engine._analyze_stride_core(doc)
    final = finalize_analysis_with_methodology(
        doc=doc,
        base=base,
        methodology=ThreatModelMethodology.LINDDUN,
        recommendation_reason="recommendation reason",
    )
    assert final.methodology == ThreatModelMethodology.LINDDUN
    assert final.methodology_recommendation_reason == "recommendation reason"
    assert final.explanations
    assert any(e.type == "methodology_recommendation" for e in final.explanations)


def test_finalize_analysis_enriches_framework_refs_and_syncs_summary() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    engine = ThreatAnalysisEngine()
    base = engine._analyze_stride_core(doc)
    assert base.heuristic_threats
    assert not any(h.framework_refs for h in base.heuristic_threats)

    final = finalize_analysis_with_methodology(
        doc=doc,
        base=base,
        methodology=ThreatModelMethodology.STRIDE,
        recommendation_reason=None,
    )
    assert any(h.framework_refs for h in final.heuristic_threats)
    active = [h for h in final.heuristic_threats if not h.skipped_as_duplicate]
    assert final.summary.heuristic_threats_generated == len(active)
    total_refs = sum(len(h.framework_refs) for h in final.heuristic_threats)
    assert total_refs == sum(final.summary.framework_ref_counts_by_catalog.values())
    assert final.explanations
