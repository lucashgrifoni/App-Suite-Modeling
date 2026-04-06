"""Testes do motor de análise."""

from pathlib import Path

from otm_core_schema import (
    Metadata,
    ModelInfo,
    RiskAssessment,
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
from otm_threat_engine.engine import suppress_stride_genericity_noise
from otm_threat_engine.result import HeuristicThreat

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
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(update={"metadata": Metadata(title="Portal LGPD com PII")})
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
    assert "plot4ai_rag_vector_composition" in ids
    finding_codes = {f.code for f in r.structural_findings}
    assert "PLOT4AI_REC_PROMPT_RETRIEVAL" in finding_codes
    assert "PLOT4AI_REC_AGENT_ISOLATION" in finding_codes
    assert "PLOT4AI_REC_VECTOR_GOVERNANCE" in finding_codes
    assert r.methodology_insights is not None
    keys = {b.key for b in r.methodology_insights.blocks}
    assert "model_interaction_layer" in keys
    assert "agent_tool_layer" in keys
    assert "vector_embedding_layer" in keys
    assert r.ai_system_context is not None
    assert r.ai_system_context.heuristic_ids_by_layer
    assert any(e.type.value == "ai_specialized_rationale" for e in r.explanations)


def test_recommendation_priority_prefers_plot4ai_over_pasta_signals() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="Enterprise attack-chain with LLM RAG agents")}
    )
    rec = recommend_methodology(doc)
    assert rec.methodology == ThreatModelMethodology.PLOT4AI


def test_recommendation_priority_prefers_pasta_over_linddun_signals() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(
        update={"metadata": Metadata(title="Advanced attack risk-centric LGPD PII context")}
    )
    rec = recommend_methodology(doc)
    assert rec.methodology == ThreatModelMethodology.PASTA


def test_explicit_methodology_supported_for_all_enum_values() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    for methodology in ThreatModelMethodology:
        result = analyze_document(doc, methodology=methodology)
        assert result.methodology == methodology


def test_octave_lens_adds_expected_engine_note() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc, methodology=ThreatModelMethodology.OCTAVE_ALLEGRO)
    notes = [f for f in result.structural_findings if f.code == "ENGINE_LENS_OCTAVE_ALLEGRO"]
    assert notes
    assert "risco de negócio" in notes[0].message.lower()


def test_cia_die_lens_keeps_top_active_threats_only() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc, methodology=ThreatModelMethodology.CIA_DIE)
    active = [h for h in result.heuristic_threats if not h.skipped_as_duplicate]
    assert len(active) <= 10


def test_no_duplicate_heuristic_ids_for_same_flow_conditions() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc, methodology=ThreatModelMethodology.STRIDE)
    flow_ids = [h.id for h in result.heuristic_threats if h.target_data_flow_id is not None]
    assert len(flow_ids) == len(set(flow_ids))


def test_summary_generated_counts_match_active_heuristics_without_pack() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc, methodology=ThreatModelMethodology.STRIDE)
    active = [h for h in result.heuristic_threats if not h.skipped_as_duplicate]
    summary_total = result.summary.heuristic_threats_generated + result.summary.pack_threats_generated
    assert summary_total == len(active)


def test_business_abuse_heuristics_present_for_finance_fixture() -> None:
    finance_doc = load_document_from_yaml_path(_ROOT / "examples" / "test-apps" / "finance-wallet.otm.yaml")
    result = analyze_document(finance_doc, methodology=ThreatModelMethodology.STRIDE)
    ids = {h.id for h in result.heuristic_threats if not h.skipped_as_duplicate}
    assert "biz_webhook_replay_economic_abuse" in ids
    assert "biz_double_submission_financial_action" in ids
    assert "biz_balance_transaction_inconsistency" in ids


def test_business_abuse_heuristics_present_for_ecommerce_fixture() -> None:
    ecommerce_doc = load_document_from_yaml_path(_ROOT / "examples" / "test-apps" / "ecommerce-subscription.otm.yaml")
    result = analyze_document(ecommerce_doc, methodology=ThreatModelMethodology.PASTA)
    active = [h for h in result.heuristic_threats if not h.skipped_as_duplicate]
    ids = {h.id for h in active}
    assert "biz_payment_entitlement_mismatch" in ids
    assert "biz_coupon_reuse_and_discount_stacking" in ids
    assert "biz_cancel_without_entitlement_revocation" in ids
    descriptions = " ".join(h.description.lower() for h in active if h.id.startswith("biz_"))
    assert "owner" in descriptions
    assert "idempot" in descriptions
    assert "econom" in descriptions


def test_phase3_engine_suppresses_stride_noise_only_when_biz_present_finance() -> None:
    finance_doc = load_document_from_yaml_path(_ROOT / "examples" / "test-apps" / "finance-wallet.otm.yaml")
    result = analyze_document(finance_doc, methodology=ThreatModelMethodology.STRIDE)

    all_ids = {h.id for h in result.heuristic_threats}
    assert "biz_webhook_replay_economic_abuse" in all_ids
    assert "eng_flow_webhook_flow_tampering" in all_ids

    active_ids = {h.id for h in result.heuristic_threats if not h.skipped_as_duplicate}
    assert "biz_webhook_replay_economic_abuse" in active_ids
    # Ruído STRIDE (cluster webhook) deve sair da visão ativa, mas continuar rastreável no JSON.
    assert "eng_flow_webhook_flow_tampering" not in active_ids

    # Controle: STRIDE fora do cluster webhook deve permanecer ativo.
    assert "eng_flow_login_flow_tampering" in active_ids


def test_phase3_engine_suppresses_stride_noise_only_when_biz_present_ecommerce() -> None:
    ecommerce_doc = load_document_from_yaml_path(_ROOT / "examples" / "test-apps" / "ecommerce-subscription.otm.yaml")
    result = analyze_document(ecommerce_doc, methodology=ThreatModelMethodology.PASTA)
    all_ids = {h.id for h in result.heuristic_threats}
    assert "biz_payment_entitlement_mismatch" in all_ids
    assert "eng_payment_gateway_tampering" in all_ids
    active_ids = {h.id for h in result.heuristic_threats if not h.skipped_as_duplicate}
    assert "biz_payment_entitlement_mismatch" in active_ids
    assert "eng_payment_gateway_tampering" not in active_ids


def test_phase3_engine_does_not_suppress_when_no_biz_families_present() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = analyze_document(doc, methodology=ThreatModelMethodology.STRIDE)
    # Documento minimal não tem `biz_*`, então não deve haver supressão adicional por Etapa 3.
    suppressed_eng = [
        h
        for h in result.heuristic_threats
        if h.id.startswith("eng_")
        and h.stride in {StrideCategory.TAMPERING, StrideCategory.ELEVATION_OF_PRIVILEGE}
        and h.skipped_as_duplicate
    ]
    assert suppressed_eng == []


def test_phase3_suppression_toggle_off_does_not_change_heuristics(monkeypatch) -> None:
    monkeypatch.setenv("OTM_ENGINE_STRIDE_NOISE_SUPPRESSION", "0")
    eng = HeuristicThreat(
        id="eng_coupon_tampering",
        title="Coupon tampering on checkout",
        description="x",
        stride=StrideCategory.TAMPERING,
        risk=RiskAssessment(likelihood=1, impact=1, score=1.0),
    )
    heuristics = [
        HeuristicThreat(
            id="biz_coupon_reuse",
            title="Coupon reuse and stacking",
            description="x",
            stride=StrideCategory.TAMPERING,
            risk=RiskAssessment(likelihood=1, impact=1, score=1.0),
        ),
        eng,
    ]
    suppressed = suppress_stride_genericity_noise(heuristics)
    assert suppressed == 0
    assert eng.skipped_as_duplicate is False


def test_phase3_suppression_toggle_on_can_mark_eng_as_skipped(monkeypatch) -> None:
    monkeypatch.setenv("OTM_ENGINE_STRIDE_NOISE_SUPPRESSION", "1")
    eng = HeuristicThreat(
        id="eng_coupon_tampering",
        title="Coupon tampering on checkout",
        description="x",
        stride=StrideCategory.TAMPERING,
        risk=RiskAssessment(likelihood=1, impact=1, score=1.0),
    )
    heuristics = [
        HeuristicThreat(
            id="biz_coupon_reuse",
            title="Coupon reuse and stacking",
            description="x",
            stride=StrideCategory.TAMPERING,
            risk=RiskAssessment(likelihood=1, impact=1, score=1.0),
        ),
        eng,
    ]
    suppressed = suppress_stride_genericity_noise(heuristics)
    assert suppressed == 1
    assert eng.skipped_as_duplicate is True
