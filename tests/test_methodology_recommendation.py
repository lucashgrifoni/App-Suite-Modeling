from pathlib import Path

from otm_core_schema import BusinessContext, Metadata, ModelInfo, load_document_from_yaml_path
from otm_core_schema.enums import IndustrySector, ThreatModelMethodology
from otm_threat_engine import recommend_methodology
from otm_threat_engine.methodology_lenses.recommendation import (
    build_recommendation_context_text,
    build_recommendation_rules,
)
from otm_threat_engine.methodology_lenses.service import recommend_with_rules

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_recommendation_defaults_to_stride_without_strong_signals() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={
            "metadata": Metadata(title="Sistema interno", summary="Aplicação corporativa genérica")
        }
    )
    rec = recommend_methodology(doc)
    assert rec.methodology == ThreatModelMethodology.STRIDE


def test_recommendation_prioritizes_ai_signals_over_other_signals() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="LLM RAG privacy attack-chain enterprise app")}
    )
    rec = recommend_methodology(doc)
    assert rec.methodology == ThreatModelMethodology.PLOT4AI


def test_recommendation_prioritizes_pasta_over_privacy_when_both_present() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={
            "metadata": Metadata(title="Advanced risk-centric attack simulation with LGPD and PII")
        }
    )
    rec = recommend_methodology(doc)
    assert rec.methodology == ThreatModelMethodology.PASTA


def test_build_recommendation_context_text_is_lowercase_and_includes_layers() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={
            "metadata": Metadata(
                title="TÍTULO",
                summary="Resumo",
                tags=["Tag1"],
            ),
            "business_context": BusinessContext(
                description="DESC corporativa",
                regulatory_context="LGPD",
            ),
        }
    )
    text = build_recommendation_context_text(doc)
    assert text == text.lower()
    assert "título" in text
    assert "resumo" in text
    assert "tag1" in text
    assert "desc corporativa" in text
    assert "lgpd" in text


def test_recommendation_rules_order_finance_triggers_nist_before_stride_fallback() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={
            "model_info": ModelInfo(
                schema_version="1.0.0",
                industry_sector=IndustrySector.FINANCE,
            ),
            "metadata": Metadata(title="Backoffice interno", summary="CRUD simples"),
        }
    )
    rec = recommend_with_rules(doc)
    assert rec.methodology == ThreatModelMethodology.NIST_DATA_CENTRIC


def test_recommendation_octave_when_asset_focus_in_text() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={
            "metadata": Metadata(
                title="Inventário de ativos críticos",
                summary="Risco organizacional",
            ),
        },
    )
    rec = recommend_with_rules(doc)
    assert rec.methodology == ThreatModelMethodology.OCTAVE_ALLEGRO


def test_build_recommendation_rules_tuple_shape() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    text = build_recommendation_context_text(doc)
    rules = build_recommendation_rules(doc, text)
    assert len(rules) == 7
    for row in rules:
        assert len(row) == 4
        pred, methodology, reason, evidence = row
        assert isinstance(pred, bool)
        assert isinstance(methodology, ThreatModelMethodology)
        assert isinstance(reason, str) and reason
        assert isinstance(evidence, list) and evidence
