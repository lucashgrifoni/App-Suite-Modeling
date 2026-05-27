"""
Benchmark oficial ampliado: expectativas em `tests/fixtures/golden/benchmark_expectations_v1.json`
+ métricas `benchmark_metrics.compute_benchmark_metrics`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from otm_core_schema import ThreatModelMethodology, load_document_from_yaml
from otm_core_schema.io import load_document_from_yaml_path
from otm_industry_packs.loader import load_pack, load_template_yaml
from otm_threat_engine import analyze_document
from otm_threat_engine.benchmark_metrics import compute_benchmark_metrics

_ROOT = Path(__file__).resolve().parents[1]
_GOLDEN = _ROOT / "tests" / "fixtures" / "golden" / "benchmark_expectations_v1.json"


def _load_expectations() -> dict:
    return json.loads(_GOLDEN.read_text(encoding="utf-8"))


def _doc(template_id: str):
    return load_document_from_yaml(load_template_yaml(template_id))


@pytest.mark.parametrize(
    "template_id",
    ["industry-ecommerce", "admin-portal", "file-upload-processing", "api-public"],
)
def test_benchmark_wave_cases_meet_golden_minimums(template_id: str) -> None:
    exp = _load_expectations()["cases"][template_id]
    doc = _doc(template_id)
    assert len(doc.assets) >= exp["min_assets"]
    assert len(doc.trust_boundaries) >= exp["min_trust_boundaries"]
    r = analyze_document(doc, methodology="stride")
    assert r.model_quality_precheck is not None
    assert r.model_quality_precheck.score_0_100 >= exp["min_model_completeness_score"]
    assert r.methodology_completeness is not None
    assert r.methodology_completeness.state.value in exp["methodology_completeness_stride"]
    m = compute_benchmark_metrics(r)
    assert m.model_completeness_score >= exp["min_model_completeness_score"]
    assert 0.0 <= m.specificity_ratio <= 1.0
    if exp.get("stride_fit_matrix_strong_or_partial") and r.model_quality_precheck:
        fit = r.model_quality_precheck.methodology_fit_matrix.get("stride", "weak")
        assert fit in ("strong", "partial")


def test_file_upload_trust_boundaries_golden() -> None:
    exp = _load_expectations()["cases"]["file-upload-processing"]
    doc = _doc("file-upload-processing")
    ids = {b.id for b in doc.trust_boundaries}
    for bid in exp["must_include_trust_boundary_ids"]:
        assert bid in ids


def test_admin_portal_finance_pack_no_payment_leakage() -> None:
    exp = _load_expectations()["cases"]["admin-portal"]
    if not exp.get("finance_pack_no_payment_keyword_in_hints"):
        return
    doc = _doc("admin-portal")
    r = analyze_document(doc, pack=load_pack("finance"), methodology="stride")
    joined = " ".join(r.pack_control_hints).lower()
    assert "pagamento" not in joined and "payment" not in joined


def test_api_public_pasta_not_complete() -> None:
    doc = _doc("api-public")
    r = analyze_document(doc, methodology=ThreatModelMethodology.PASTA)
    assert r.methodology_completeness is not None
    assert r.methodology_completeness.state.value != "complete"


def test_nist_dc_partial_golden_sample() -> None:
    raw = """
model:
  schema_version: "1.1.0"
  methodology: nist_data_centric
metadata:
  title: NIST sample
components:
  - id: x
    name: X
    kind: process
data_flows: []
assets:
  - id: blob
    name: "Blob"
    asset_kind: data
trust_boundaries: []
threats: []
mitigations: []
evidence_suggestions: []
"""
    doc = load_document_from_yaml(raw)
    r = analyze_document(doc, methodology=ThreatModelMethodology.NIST_DATA_CENTRIC)
    assert r.methodology_completeness is not None
    assert r.methodology_completeness.state.value == "partial"


def test_benchmark_metrics_has_expected_keys() -> None:
    doc = load_document_from_yaml_path(_ROOT / "examples" / "minimal.otm.yaml")
    r = analyze_document(doc)
    m = compute_benchmark_metrics(r)
    assert m.top_10_actionability_score >= 0.0
    assert m.methodology_delta >= 0.0
    assert 0.0 <= m.anti_pattern_signal_density <= 1.0
    assert m.recommendation_relevance_score >= 0.0
    assert m.semantic_alignment_score >= 0.0
