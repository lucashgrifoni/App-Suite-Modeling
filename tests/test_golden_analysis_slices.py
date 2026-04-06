"""
Regressão semântica leve: subconjuntos estáveis da análise por template (sem snapshot gigante).
"""

from __future__ import annotations

import json
from pathlib import Path

from otm_core_schema import load_document_from_yaml
from otm_industry_packs.loader import load_template_yaml
from otm_threat_engine import analyze_document

_ROOT = Path(__file__).resolve().parents[1]
_SLICE = _ROOT / "tests" / "fixtures" / "golden" / "analysis_slice_expectations_v1.json"


def _expectations() -> dict:
    return json.loads(_SLICE.read_text(encoding="utf-8"))


def test_golden_slice_api_public_stride() -> None:
    exp = _expectations()["cases"]["api-public-stride"]
    doc = load_document_from_yaml(load_template_yaml("api-public"))
    r = analyze_document(doc, methodology="stride")
    assert r.model_quality_precheck is not None
    assert r.model_quality_precheck.score_0_100 >= exp["min_model_quality_score"]
    assert r.methodology_completeness is not None
    assert len(r.heuristic_threats) >= exp["min_heuristic_threats"]


def test_golden_slice_has_wizard_field_in_contract() -> None:
    doc = load_document_from_yaml(load_template_yaml("api-public"))
    r = analyze_document(doc)
    d = r.model_dump(mode="json")
    assert "wizard_context_notes" in d
    assert isinstance(d["wizard_context_notes"], list)
