"""Contrato do mapa de lentes (dispatch) por metodologia."""

from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_core_schema.enums import ThreatModelMethodology
from otm_threat_engine import analyze_document
from otm_threat_engine.methodology_lenses.dispatch import build_lens_dispatch
from otm_threat_engine.result import AnalysisResult

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_build_lens_dispatch_covers_all_methodology_enum_values() -> None:
    dispatch = build_lens_dispatch()
    assert set(dispatch.keys()) == set(ThreatModelMethodology)


def test_each_lens_handler_returns_analysis_result() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    base = analyze_document(doc, methodology=ThreatModelMethodology.STRIDE)
    dispatch = build_lens_dispatch()
    for _methodology, handler in dispatch.items():
        out = handler(doc, base.model_copy(deep=True))
        assert isinstance(out, AnalysisResult)
        assert out.document_title == base.document_title
        assert out.engine_version == base.engine_version
