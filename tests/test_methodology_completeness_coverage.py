"""Coverage — methodology completeness assessment across degraded/partial states."""

from __future__ import annotations

from otm_core_schema import ThreatModelMethodology, create_blank_document
from otm_core_schema.enums import MethodologyCompletenessState
from otm_threat_engine.methodology_completeness import assess_methodology_completeness


def _no_assets():
    return create_blank_document().model_copy(update={"assets": []})


def test_stride_few_components_partial() -> None:
    doc = create_blank_document()  # 0 components, has a trust boundary
    info = assess_methodology_completeness(doc, ThreatModelMethodology.STRIDE)
    assert info.state == MethodologyCompletenessState.PARTIAL
    assert info.reasons


def test_pasta_no_objectives_no_assets_degraded() -> None:
    info = assess_methodology_completeness(_no_assets(), ThreatModelMethodology.PASTA)
    assert info.state == MethodologyCompletenessState.DEGRADED


def test_nist_no_assets_degraded() -> None:
    info = assess_methodology_completeness(_no_assets(), ThreatModelMethodology.NIST_DATA_CENTRIC)
    assert info.state == MethodologyCompletenessState.DEGRADED


def test_octave_and_cia_no_assets_partial() -> None:
    for m in (ThreatModelMethodology.OCTAVE_ALLEGRO, ThreatModelMethodology.CIA_DIE):
        info = assess_methodology_completeness(_no_assets(), m)
        assert info.state == MethodologyCompletenessState.PARTIAL
        assert info.note is not None


def test_plot4ai_no_corpus_partial() -> None:
    info = assess_methodology_completeness(create_blank_document(), ThreatModelMethodology.PLOT4AI)
    assert info.state == MethodologyCompletenessState.PARTIAL
