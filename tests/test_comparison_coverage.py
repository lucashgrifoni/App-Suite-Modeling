"""Coverage — semantic comparison deltas + comparison markdown (pack hints, quality/methodology)."""

from __future__ import annotations

from pathlib import Path

from otm_core_schema import ThreatModelMethodology, load_document_from_yaml_path
from otm_exporters import export_comparison_markdown
from otm_industry_packs.loader import load_pack
from otm_threat_engine import analyze_document, compare_threat_models

_ROOT = Path(__file__).resolve().parents[1]
_RICH = _ROOT / "examples" / "saas-ordering-v1.otm.yaml"
_SPARSE = _ROOT / "examples" / "minimal.otm.yaml"


def test_compare_with_quality_and_methodology_and_pack_deltas() -> None:
    doc_a = load_document_from_yaml_path(_RICH)
    doc_b = load_document_from_yaml_path(_SPARSE)
    pack = load_pack("saas")
    # baseline richer + pack (more pack hints, higher quality) vs revised sparser + different methodology
    a_base = analyze_document(doc_a, pack=pack, methodology=ThreatModelMethodology.STRIDE)
    a_rev = analyze_document(doc_b, methodology=ThreatModelMethodology.LINDDUN)
    result = compare_threat_models(doc_a, doc_b, baseline_analysis=a_base, revised_analysis=a_rev)
    md = export_comparison_markdown(result)
    assert md and isinstance(md, str)


def test_compare_reverse_direction_improves() -> None:
    doc_a = load_document_from_yaml_path(_SPARSE)
    doc_b = load_document_from_yaml_path(_RICH)
    pack = load_pack("saas")
    a_base = analyze_document(doc_a, methodology=ThreatModelMethodology.LINDDUN)
    a_rev = analyze_document(doc_b, pack=pack, methodology=ThreatModelMethodology.STRIDE)
    result = compare_threat_models(doc_a, doc_b, baseline_analysis=a_base, revised_analysis=a_rev)
    assert export_comparison_markdown(result)


def test_compare_structural_only_no_analysis() -> None:
    doc_a = load_document_from_yaml_path(_RICH)
    doc_b = load_document_from_yaml_path(_SPARSE)
    result = compare_threat_models(doc_a, doc_b)
    assert export_comparison_markdown(result)
