"""Insights semânticos na comparação de modelos."""

from __future__ import annotations

from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_threat_engine import analyze_document
from otm_threat_engine.comparison_models import DiffAggregate
from otm_threat_engine.semantic_comparison import enrich_comparison_meta
from otm_threat_engine.threat_model_comparison import compare_threat_models

_ROOT = Path(__file__).resolve().parents[1]
_MIN = _ROOT / "examples" / "minimal.otm.yaml"


def test_enrich_comparison_meta_includes_semantic_insights_version() -> None:
    base = load_document_from_yaml_path(_MIN)
    rev = load_document_from_yaml_path(_MIN)
    agg = DiffAggregate(
        components={"added": [], "removed": [], "changed": []},
        assets={"added": [], "removed": [], "changed": []},
        data_flows={"added": [], "removed": [], "changed": []},
        trust_boundaries={"added": ["dmz"], "removed": [], "changed": []},
        threats={"added": [], "removed": [], "changed": []},
        mitigations={"added": [], "removed": [], "changed": []},
        evidence_suggestions={"added": [], "removed": [], "changed": []},
    )
    meta = enrich_comparison_meta(
        base,
        rev,
        baseline_analysis=None,
        revised_analysis=None,
        aggregate=agg,
    )
    assert meta.get("semantic_insights_version") == "1.1"
    assert "semantic_diff_sections" in meta
    assert any("dmz" in s for s in meta.get("semantic_insights", []))


def test_compare_merges_meta_insights() -> None:
    a = load_document_from_yaml_path(_MIN)
    b = load_document_from_yaml_path(_MIN)
    ra = analyze_document(b)
    r = compare_threat_models(a, b, baseline_analysis=ra, revised_analysis=ra)
    assert "semantic_insights" in r.meta or "comparison_contract_version" in r.meta
