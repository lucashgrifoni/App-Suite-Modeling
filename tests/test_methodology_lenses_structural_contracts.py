"""Códigos estáveis de StructuralFinding e heurísticas-chave por ficheiro de lente."""

from __future__ import annotations

from pathlib import Path

from otm_core_schema import Metadata, load_document_from_yaml_path
from otm_core_schema.enums import ThreatModelMethodology
from otm_threat_engine import analyze_document
from otm_threat_engine.methodology_lenses.dispatch import build_lens_dispatch
from otm_threat_engine.methodology_lenses.linddun import apply_linddun_lens
from otm_threat_engine.methodology_lenses.nist_data_centric import apply_nist_data_centric_lens
from otm_threat_engine.methodology_lenses.pasta import apply_pasta_lens
from otm_threat_engine.methodology_lenses.plot4ai import apply_plot4ai_lens
from otm_threat_engine.result import AnalysisResult

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def _finding_codes(result: AnalysisResult) -> set[str]:
    return {f.code for f in result.structural_findings}


def test_linddun_lens_stable_codes_and_heuristics_with_pii_context() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="x", summary="Tratamento de dados pessoais")}
    )
    base = analyze_document(doc, methodology=ThreatModelMethodology.STRIDE)
    out = apply_linddun_lens(doc, base.model_copy(deep=True))
    codes = _finding_codes(out)
    assert "LINDDUN_REC_CONSENT" in codes
    assert "LINDDUN_REC_MINIMIZATION" in codes
    assert "LINDDUN_REC_RETENTION" in codes
    assert "LINDDUN_REC_EXPOSURE" in codes
    assert "ENGINE_LENS_LINDDUN" in codes
    assert any(h.id.startswith("linddun_") for h in out.heuristic_threats)


def test_nist_data_centric_lens_stable_prep_focus_and_engine_codes() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    base = analyze_document(doc, methodology=ThreatModelMethodology.STRIDE)
    out = apply_nist_data_centric_lens(base.model_copy(deep=True))
    codes = _finding_codes(out)
    for code in (
        "NIST_DC_PREP_CLASSIFICATION",
        "NIST_DC_PREP_DATA_PATHS",
        "NIST_DC_PREP_CONTROLS",
        "NIST_DC_FOCUS_DATA_PROTECTION",
        "NIST_DC_FOCUS_ACCESS",
        "NIST_DC_FOCUS_AUDIT",
        "NIST_DC_FOCUS_SEGREGATION",
        "ENGINE_LENS_NIST_DATA_CENTRIC",
    ):
        assert code in codes


def test_pasta_lens_stable_risk_codes_and_core_heuristic_ids() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    base = analyze_document(doc, methodology=ThreatModelMethodology.STRIDE)
    out = apply_pasta_lens(doc, base.model_copy(deep=True))
    codes = _finding_codes(out)
    for code in (
        "PASTA_RISK_SURFACE",
        "PASTA_RISK_INTEGRATIONS",
        "PASTA_RISK_IMPACT",
        "ENGINE_LENS_PASTA",
    ):
        assert code in codes
    ids = {h.id for h in out.heuristic_threats}
    assert "pasta_attack_chain_abuse" in ids
    assert "pasta_vulnerability_exposure" in ids


def test_plot4ai_lens_stable_recommendation_codes() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    base = analyze_document(doc, methodology=ThreatModelMethodology.STRIDE)
    out = apply_plot4ai_lens(doc, base.model_copy(deep=True))
    codes = _finding_codes(out)
    for code in (
        "PLOT4AI_REC_PROMPT_RETRIEVAL",
        "PLOT4AI_REC_AGENT_ISOLATION",
        "PLOT4AI_REC_IO_VALIDATION",
        "PLOT4AI_REC_VECTOR_GOVERNANCE",
        "PLOT4AI_REC_GOVERNANCE_OBSERVABILITY",
        "ENGINE_LENS_PLOT4AI",
    ):
        assert code in codes


def test_plot4ai_lens_adds_stable_ai_heuristics_when_context_has_llm_and_rag() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={
            "metadata": Metadata(
                title="Assistente LLM",
                summary="Pipeline com RAG e validação de prompt do utilizador",
            )
        }
    )
    base = analyze_document(doc, methodology=ThreatModelMethodology.STRIDE)
    out = apply_plot4ai_lens(doc, base.model_copy(deep=True))
    ids = {h.id for h in out.heuristic_threats}
    assert "plot4ai_prompt_input_handling" in ids
    assert "plot4ai_retrieval_grounding" in ids


def test_dispatch_octave_and_cia_die_emit_engine_lens_codes() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    base = analyze_document(doc, methodology=ThreatModelMethodology.STRIDE)
    dispatch = build_lens_dispatch()
    for methodology, expected in (
        (ThreatModelMethodology.OCTAVE_ALLEGRO, "ENGINE_LENS_OCTAVE_ALLEGRO"),
        (ThreatModelMethodology.CIA_DIE, "ENGINE_LENS_CIA_DIE"),
    ):
        out = dispatch[methodology](doc, base.model_copy(deep=True))
        assert expected in _finding_codes(out)


def test_stride_dispatch_does_not_append_engine_lens_finding() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    base = analyze_document(doc, methodology=ThreatModelMethodology.STRIDE)
    dispatch = build_lens_dispatch()
    out = dispatch[ThreatModelMethodology.STRIDE](doc, base.model_copy(deep=True))
    assert [f.code for f in out.structural_findings] == [f.code for f in base.structural_findings]
