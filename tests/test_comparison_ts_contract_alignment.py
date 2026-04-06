"""
Contrato JSON de `ThreatModelComparisonResult`: chaves de primeira ordem alinhadas ao SPA.

`apps/web/src/types/api.ts` deve declarar `analysis`, `threat_delta`, `meta` sem tipagem frouxa
nos pontos críticos (ver interfaces `AnalysisDiff`, `ThreatDeltaSummary`, `ComparisonMeta`).
"""

from __future__ import annotations

from otm_threat_engine.comparison_models import ThreatModelComparisonResult

_TS_COMPARISON_TOP_LEVEL = frozenset(
    {
        "summary",
        "aggregate",
        "structural",
        "structural_insights",
        "analysis",
        "analysis_insights",
        "risk_delta",
        "threat_delta",
        "recommendation_delta",
        "key_insights",
        "meta",
        "explanations",
    }
)


def test_comparison_result_model_includes_ts_contract_fields() -> None:
    names = set(ThreatModelComparisonResult.model_fields.keys())
    missing = sorted(_TS_COMPARISON_TOP_LEVEL - names)
    assert not missing, f"ThreatModelComparisonResult lacks fields expected by TS contract: {missing}"


def test_comparison_meta_semantic_keys_stable() -> None:
    """Garante que chaves de meta usadas na UI/export permanecem estáveis (raiz fechada + `extensions`)."""
    # enrich_comparison_meta devolve estes keys; falha se renomear sem actualizar TS/CLI/markdown.
    from pathlib import Path

    from otm_core_schema import load_document_from_yaml_path
    from otm_threat_engine.comparison_models import DiffAggregate
    from otm_threat_engine.semantic_comparison import enrich_comparison_meta

    root = Path(__file__).resolve().parents[1]
    doc = load_document_from_yaml_path(root / "examples" / "minimal.otm.yaml")
    agg = DiffAggregate(
        components={"added": ["x"], "removed": [], "changed": []},
        assets={"added": [], "removed": [], "changed": []},
        data_flows={"added": [], "removed": [], "changed": []},
        trust_boundaries={"added": [], "removed": [], "changed": []},
        threats={"added": [], "removed": [], "changed": []},
        mitigations={"added": [], "removed": [], "changed": []},
        evidence_suggestions={"added": [], "removed": [], "changed": []},
    )
    meta = enrich_comparison_meta(doc, doc, baseline_analysis=None, revised_analysis=None, aggregate=agg)
    for key in (
        "semantic_insights",
        "semantic_insights_version",
        "semantic_diff_sections",
        "semantic_structural_refs",
        "semantic_interpretation_links",
        "interpretation_disclaimer",
    ):
        assert key in meta, f"meta missing stable key {key}"
    assert meta.get("semantic_insights_version") == "1.5"
