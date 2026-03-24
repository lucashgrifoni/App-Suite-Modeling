"""Testes do motor de análise."""

from pathlib import Path

from otm_core_schema import (
    Metadata,
    ModelInfo,
    Threat,
    ThreatModelDocument,
    load_document_from_yaml_path,
)
from otm_core_schema.enums import StrideCategory, ThreatModelMethodology, TreatmentStatus
from otm_threat_engine import (
    analyze_document,
    merge_heuristic_threats,
    recommend_methodology,
)

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_analyze_minimal_has_heuristics_and_crossings() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = analyze_document(doc)
    assert r.document_title
    assert r.summary.heuristic_threats_generated > 0
    assert r.summary.max_risk_score is not None
    crossing = [f for f in r.trust_boundary_findings if f.code == "CROSS_BOUNDARY_FLOW"]
    assert len(crossing) >= 1


def test_risk_score_is_product() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = analyze_document(doc)
    for h in r.heuristic_threats:
        if h.skipped_as_duplicate:
            continue
        assert h.risk.score == float(h.risk.likelihood * h.risk.impact)


def test_skips_duplicate_when_threat_exists() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    # Colide com a heurística do utilizador (primeiro componente): SPOOFING em `user`
    doc2 = doc.model_copy(
        update={
            "threats": [
                *doc.threats,
                Threat(
                    id="manual_dup",
                    title="dup",
                    stride=StrideCategory.SPOOFING,
                    target_component_id="user",
                    treatment_status=TreatmentStatus.NEW,
                ),
            ]
        }
    )
    r2 = analyze_document(doc2)
    assert r2.summary.heuristic_threats_skipped_duplicate >= 1


def test_structural_warning_no_components() -> None:
    doc = ThreatModelDocument(
        model_info=ModelInfo(),
        metadata=Metadata(title="empty"),
        components=[],
    )
    r = analyze_document(doc)
    codes = {f.code for f in r.structural_findings}
    assert "EMPTY_COMPONENTS" in codes


def test_merge_adds_threats() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = analyze_document(doc)
    merged = merge_heuristic_threats(doc, r.heuristic_threats)
    assert len(merged.threats) >= len(doc.threats)


def test_trust_insight_message_contains_flow_id() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = analyze_document(doc)
    http_cross = [x for x in r.trust_boundary_findings if x.data_flow_id == "http_in"]
    assert http_cross
    assert "http_in" in http_cross[0].message


def test_methodology_explicit_cia_die_changes_output_shape() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = analyze_document(doc, methodology=ThreatModelMethodology.CIA_DIE)
    assert r.methodology == ThreatModelMethodology.CIA_DIE
    active = [h for h in r.heuristic_threats if not h.skipped_as_duplicate]
    assert len(active) <= 10


def test_auto_recommend_methodology_for_privacy_context() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="Portal LGPD com PII")}
    )
    rec = recommend_methodology(doc)
    assert rec.methodology == ThreatModelMethodology.LINDDUN
    r = analyze_document(doc, auto_recommend=True)
    assert r.methodology == ThreatModelMethodology.LINDDUN
    assert r.methodology_recommendation_reason


def test_linddun_adds_native_privacy_heuristics() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={
            "metadata": Metadata(
                title="Portal LGPD com PII",
                summary="Fluxos com dados pessoais e consentimento",
            )
        }
    )
    r = analyze_document(doc, methodology=ThreatModelMethodology.LINDDUN)
    active = [h for h in r.heuristic_threats if not h.skipped_as_duplicate]
    linddun_native = [h for h in active if h.id.startswith("linddun_")]
    assert linddun_native, "deveria gerar heurísticas nativas LINDDUN"
    titles = " ".join(h.title.lower() for h in linddun_native)
    assert "consent" in titles or "divulgação" in titles or "identificação" in titles


def test_linddun_phase2_covers_main_privacy_categories_and_recommendations() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={
            "metadata": Metadata(
                title="Plataforma LGPD com PII e privacidade",
                summary="Consentimento, retenção e minimização de dados pessoais",
            )
        }
    )
    r = analyze_document(doc, methodology=ThreatModelMethodology.LINDDUN)
    active_ids = {h.id for h in r.heuristic_threats if not h.skipped_as_duplicate}
    assert any("_linkability" in hid for hid in active_ids)
    assert any("_identification" in hid for hid in active_ids)
    assert any("_detectability" in hid for hid in active_ids)
    assert any("_disclosure" in hid for hid in active_ids)
    assert any("_unawareness" in hid for hid in active_ids)
    assert any("_non_compliance" in hid for hid in active_ids)

    finding_codes = {f.code for f in r.structural_findings}
    assert "LINDDUN_REC_CONSENT" in finding_codes
    assert "LINDDUN_REC_MINIMIZATION" in finding_codes
    assert "LINDDUN_REC_RETENTION" in finding_codes
    assert "LINDDUN_REC_EXPOSURE" in finding_codes


def test_recommend_plot4ai_for_ai_context() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="API de inferência LLM com RAG e agentes")}
    )
    rec = recommend_methodology(doc)
    assert rec.methodology == ThreatModelMethodology.PLOT4AI
    r = analyze_document(doc, auto_recommend=True)
    assert r.methodology == ThreatModelMethodology.PLOT4AI
    assert any(h.id.startswith("plot4ai_") for h in r.heuristic_threats)


def test_recommend_pasta_for_advanced_risk_context() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="Enterprise attack-chain risk-centric assessment")}
    )
    rec = recommend_methodology(doc)
    assert rec.methodology == ThreatModelMethodology.PASTA
    r = analyze_document(doc, methodology=ThreatModelMethodology.PASTA)
    assert r.methodology == ThreatModelMethodology.PASTA
    assert any(h.id.startswith("pasta_") for h in r.heuristic_threats)
    assert r.methodology_insights is not None
    assert r.methodology_insights.profile
    block_keys = {b.key for b in r.methodology_insights.blocks}
    assert "attack_surface" in block_keys
    assert "risk_oriented_findings" in block_keys


def test_nist_data_centric_contains_v1_preparation_notes() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = analyze_document(doc, methodology=ThreatModelMethodology.NIST_DATA_CENTRIC)
    finding_codes = {f.code for f in r.structural_findings}
    assert "NIST_DC_PREP_CLASSIFICATION" in finding_codes
    assert "NIST_DC_PREP_DATA_PATHS" in finding_codes
    assert "NIST_DC_PREP_CONTROLS" in finding_codes


def test_nist_data_centric_v1_adds_data_centric_heuristics_and_focus() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={
            "metadata": Metadata(
                title="Plataforma de pagamentos com dados pessoais e trilha de auditoria",
                summary="Dados sensíveis em trânsito, em repouso e em uso",
            )
        }
    )
    r = analyze_document(doc, methodology=ThreatModelMethodology.NIST_DATA_CENTRIC)
    active_ids = {h.id for h in r.heuristic_threats if not h.skipped_as_duplicate}
    assert any(hid.startswith("nist_dc_classified_data_") for hid in active_ids)
    assert any(hid.startswith("nist_dc_sensitive_path_") for hid in active_ids)
    assert any(hid.startswith("nist_dc_in_transit_") for hid in active_ids)
    assert any(hid.startswith("nist_dc_at_rest_") for hid in active_ids)
    assert any(hid.startswith("nist_dc_in_use_") for hid in active_ids)

    finding_codes = {f.code for f in r.structural_findings}
    assert "NIST_DC_FOCUS_DATA_PROTECTION" in finding_codes
    assert "NIST_DC_FOCUS_ACCESS" in finding_codes
    assert "NIST_DC_FOCUS_AUDIT" in finding_codes
    assert "NIST_DC_FOCUS_SEGREGATION" in finding_codes


def test_plot4ai_phase2_adds_subdomain_insights_and_recommendations() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={
            "metadata": Metadata(
                title="Agentic LLM app com RAG embeddings e tool use",
                summary="pipeline de inferência com retrieval e prompts",
            )
        }
    )
    r = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    ids = {h.id for h in r.heuristic_threats}
    assert "plot4ai_prompt_input_handling" in ids
    assert "plot4ai_retrieval_grounding" in ids
    assert "plot4ai_agent_tool_execution" in ids
    assert "plot4ai_governance_pipeline" in ids
    finding_codes = {f.code for f in r.structural_findings}
    assert "PLOT4AI_REC_PROMPT_RETRIEVAL" in finding_codes
    assert "PLOT4AI_REC_AGENT_ISOLATION" in finding_codes
    assert r.methodology_insights is not None
    keys = {b.key for b in r.methodology_insights.blocks}
    assert "model_interaction_risks" in keys
    assert "agent_tool_execution_risks" in keys
