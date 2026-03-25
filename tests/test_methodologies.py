"""Contratos dos wrappers públicos em `methodologies.py` (sem lógica extra)."""

from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_core_schema.enums import ThreatModelMethodology
from otm_threat_engine import analyze_document
from otm_threat_engine.methodologies import apply_methodology_lens, recommend_methodology
from otm_threat_engine.methodology_lenses.service import apply_with_dispatch, recommend_with_rules

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_recommend_methodology_delegates_to_recommend_with_rules() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    a = recommend_methodology(doc)
    b = recommend_with_rules(doc)
    assert a.methodology == b.methodology
    assert a.reason == b.reason


def test_apply_methodology_lens_delegates_to_apply_with_dispatch() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    base = analyze_document(doc, methodology=ThreatModelMethodology.STRIDE)
    via_public = apply_methodology_lens(doc, base, methodology=ThreatModelMethodology.PASTA)
    via_service = apply_with_dispatch(doc, base, methodology=ThreatModelMethodology.PASTA)
    assert via_public.model_dump() == via_service.model_dump()
