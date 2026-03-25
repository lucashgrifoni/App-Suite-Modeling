from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_threat_engine import analyze_document
from otm_threat_engine.framework_refs import enrich_analysis_framework_refs, enrich_heuristic_threat

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_enrich_heuristic_threat_adds_framework_refs() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = enrich_analysis_framework_refs(analyze_document(doc))
    sample = result.heuristic_threats[0]
    enriched = enrich_heuristic_threat(sample)
    assert enriched.framework_refs


def test_enrich_analysis_framework_refs_updates_summary_counts() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    base = analyze_document(doc)
    enriched = enrich_analysis_framework_refs(base)
    total = sum(enriched.summary.framework_ref_counts_by_catalog.values())
    assert total == sum(len(h.framework_refs) for h in enriched.heuristic_threats)


def test_enrich_analysis_framework_refs_is_idempotent() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    base = analyze_document(doc)
    enriched1 = enrich_analysis_framework_refs(base)
    enriched2 = enrich_analysis_framework_refs(enriched1)
    assert enriched2.model_dump() == enriched1.model_dump()


def test_framework_ref_counts_keys_are_sorted() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    enriched = enrich_analysis_framework_refs(analyze_document(doc))
    keys = list(enriched.summary.framework_ref_counts_by_catalog.keys())
    assert keys == sorted(keys)
