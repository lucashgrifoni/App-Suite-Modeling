"""Insights semânticos na comparação de modelos."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_core_schema.document import TrustBoundary
from otm_exporters.comparison_markdown import export_comparison_markdown
from otm_threat_engine import analyze_document
from otm_threat_engine.comparison_models import DiffAggregate
from otm_threat_engine.semantic_comparison import enrich_comparison_meta, semantic_diff_from_analyses_only
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
    assert meta.get("semantic_insights_version") == "1.4"
    assert "semantic_diff_sections" in meta
    assert any("dmz" in s for s in meta.get("semantic_insights", []))
    assert meta.get("semantic_structural_refs")
    assert any(r.get("ref", "").startswith("struct:trust_boundary_added:") for r in meta["semantic_structural_refs"])
    links = meta.get("semantic_interpretation_links")
    assert isinstance(links, list)
    assert links, "v1.4 espera pelo menos uma ligação quando há boundary + bullets com tokens em comum"
    assert all("link_kind" in x and "inference_strength" in x for x in links)
    assert any(x.get("link_kind") == "lexical_token_overlap" for x in links)


def test_compare_merges_meta_insights() -> None:
    a = load_document_from_yaml_path(_MIN)
    b = load_document_from_yaml_path(_MIN)
    ra = analyze_document(b)
    r = compare_threat_models(a, b, baseline_analysis=ra, revised_analysis=ra)
    assert r.meta.comparison_contract_version == "1.4"
    assert isinstance(r.meta.semantic_insights, list)


def test_semantic_diff_from_analyses_only_detects_quality_delta() -> None:
    base = analyze_document(load_document_from_yaml_path(_MIN))
    assert base.model_quality_precheck is not None
    pq = base.model_quality_precheck
    rev = base.model_copy(
        update={
            "model_quality_precheck": pq.model_copy(update={"score_0_100": max(0, pq.score_0_100 - 15)}),
        }
    )
    ins, _imp, wor, _risk = semantic_diff_from_analyses_only(base, rev)
    joined = " ".join(ins + wor).lower()
    assert "pré-check" in joined or "model quality" in joined


def test_comparison_markdown_includes_semantic_diff_summary() -> None:
    base = load_document_from_yaml_path(_MIN)
    revised = deepcopy(base)
    revised.trust_boundaries = [*revised.trust_boundaries, TrustBoundary(id="dmz_e2e", name="DMZ E2E")]
    cmp = compare_threat_models(base, revised)
    md = export_comparison_markdown(cmp)
    assert "### Diff semântico (resumo)" in md
    assert "### Aviso inferencial (diff)" in md
    assert "### Ligação estrutura → interpretação (refs estáveis)" in md
    sem = cmp.meta.semantic_diff_sections
    if sem is not None and sem.risk_impact:
        assert any("Segmentação" in x or "perímetro" in x for x in sem.risk_impact)
    assert "### Insights semânticos (narrativa)" in md
    assert "### Correspondência ref → interpretação (v1.4)" in md
