"""
Textos estruturais do report premium (pt-BR / en).

Conteúdo dinâmico do motor permanece inalterado; apenas rótulos e frases de template.
"""

from __future__ import annotations

from dataclasses import dataclass

from .i18n_locale import PremiumReportLocale


@dataclass(frozen=True)
class PremiumBuilderCopy:
    status_requires_immediate: str
    status_action_recommended: str
    status_acceptable_plain: str
    status_acceptable_no_aggregate: str
    risk_not_calculated: str
    risk_elevated: str
    risk_high: str
    risk_medium: str
    risk_low_moderate: str
    readiness_high: str
    readiness_moderate: str
    readiness_release: str
    readiness_compensating: str
    exec_conclusion: str
    arch_counts: str
    default_threat_action: str
    ownership_scope: str
    owner_pending_display: str
    ownership_explanation: str
    strategic_baseline_title: str
    strategic_baseline_detail: str
    strategic_integrations_title: str
    strategic_integrations_detail: str
    strategic_pack_title: str
    roadmap_immediate: str
    roadmap_short: str
    roadmap_medium: str
    tb_delta: str
    struct_delta: str
    baseline_narrative: str
    tech_methodology_outputs: str
    tech_import_evidence: str
    disclaimer_summary: str
    disclaimer_b1: str
    disclaimer_b2: str
    business_impact_summary: str
    mq_line: str
    mc_line_prefix: str
    threat_canonical_prefix: str
    wizard_trace: str


@dataclass(frozen=True)
class PremiumRenderCopy:
    md_em_dash: str
    md_no_data: str
    nd: str
    md_executive_cover: str
    md_schema_version: str
    md_primary_methodology: str
    md_system_sector: str
    md_analysis_date: str
    md_app_version: str
    md_risk_class: str
    md_overall_state: str
    md_inference_notice: str
    md_executive_summary: str
    md_total_threats: str
    md_urgency: str
    md_exec_conclusion: str
    md_sev_distribution: str
    hdr_severity: str
    hdr_count: str
    md_meth_distribution: str
    hdr_methodology: str
    hdr_threats: str
    md_top_tb: str
    md_top_surfaces: str
    md_top5_titles: str
    md_readiness_questions: str
    md_none_listed: str
    md_guided_context: str
    md_model_quality: str
    md_methodology_line: str
    md_wizard_notes: str
    md_audit_trail: str
    md_gap_precheck: str
    md_anti_patterns: str
    md_arch_overview: str
    md_main_components: str
    md_main_flows: str
    md_meth_used_vs_rec: str
    md_used: str
    md_recommended: str
    md_reason: str
    md_stats_distribution: str
    hdr_metric: str
    hdr_value: str
    md_total_threats_metric: str
    md_by_stride: str
    hdr_stride: str
    hdr_n: str
    md_heatmap_stride_sev: str
    md_ranking_components: str
    hdr_component: str
    hdr_score: str
    md_top10_risks: str
    hdr_rank: str
    hdr_id: str
    hdr_title: str
    hdr_p: str
    hdr_tier: str
    hdr_action_short: str
    md_root_cause_groups: str
    md_occurrences_backlog: str
    md_single_fix: str
    md_controls: str
    md_exploit_sample: str
    md_locality: str
    md_external: str
    md_mitm: str
    md_business_impact_labels: str
    md_quick_wins: str
    md_ownership: str
    md_to_define: str
    md_items: str
    md_strategic: str
    md_roadmap: str
    md_baseline_diff: str
    md_new: str
    md_removed: str
    md_semantic_diff: str
    md_semantic_diff_note: str
    md_improved: str
    md_attention: str
    md_risk_impact_reading: str
    md_dedup: str
    md_dedup_ids: str
    md_explainability: str
    md_technical_appendix: str
    md_threats_excerpt: str
    md_appendix_coverage: str
    md_appendix_truncated: str
    md_methodology_adaptation: str
    md_footer: str
    html_lang: str
    html_inference: str
    html_exec_summary: str
    html_total_threats: str
    html_urgency: str
    html_top_risks: str
    html_th_rank: str
    html_th_id: str
    html_th_title: str
    html_th_tier: str
    html_th_p: str
    html_root_causes: str
    html_roadmap: str
    html_baseline: str
    html_meta_schema: str
    html_meta_methodology: str
    html_meta_date: str
    html_meta_product_version: str
    html_state: str
    html_risk_heuristic: str
    html_footer: str


ROOT_CAUSE_LABELS_PT: dict[str, str] = {
    "identity_and_authorization_gaps": "Autenticação / autorização",
    "data_exposure_and_classification": "Dados sensíveis sem proteção suficiente",
    "integrity_and_supply_chain": "Integridade / cadeia de fornecimento",
    "availability_and_resilience": "Disponibilidade e resiliência",
    "non_repudiation_and_audit": "Não repúdio e auditoria",
    "third_party_trust": "Integrações third-party",
    "ai_governance_and_model_risk": "Governança e risco de modelo (AI/LLM)",
    "general_mitigation": "Mitigação geral",
    "trust_perimeter_crossing": "Cruzamento de trust boundary",
    "threat_model_hygiene": "Higiene do artefacto de threat model",
    "industry_pack_recommendation": "Recomendações do industry pack",
}

ROOT_CAUSE_LABELS_EN: dict[str, str] = {
    "identity_and_authorization_gaps": "Authentication / authorization",
    "data_exposure_and_classification": "Sensitive data without sufficient protection",
    "integrity_and_supply_chain": "Integrity / supply chain",
    "availability_and_resilience": "Availability and resilience",
    "non_repudiation_and_audit": "Non-repudiation and audit",
    "third_party_trust": "Third-party integrations",
    "ai_governance_and_model_risk": "AI/LLM governance and model risk",
    "general_mitigation": "General mitigation",
    "trust_perimeter_crossing": "Trust boundary crossing",
    "threat_model_hygiene": "Threat model artifact hygiene",
    "industry_pack_recommendation": "Industry pack recommendations",
}


def root_cause_display_name(key: str, locale: PremiumReportLocale) -> str:
    labels = ROOT_CAUSE_LABELS_EN if locale == "en" else ROOT_CAUSE_LABELS_PT
    return labels.get(key, key.replace("_", " ").title())


_BUILDER_PT = PremiumBuilderCopy(
    status_requires_immediate="Requer atenção imediata",
    status_action_recommended="Acção recomendada",
    status_acceptable_plain="Aceitável com acompanhamento",
    status_acceptable_no_aggregate="Aceitável com acompanhamento (sem score agregado)",
    risk_not_calculated="não calculado",
    risk_elevated="elevado",
    risk_high="alto",
    risk_medium="médio",
    risk_low_moderate="baixo a moderado",
    readiness_high="O modelo indica risco elevado à luz das heurísticas actuais?",
    readiness_moderate="Os scores são moderados — validar com testes e contexto de negócio.",
    readiness_release="O sistema parece pronto para release com estes achados em aberto?",
    readiness_compensating="Existem controlos compensatórios ou aceitação formal de risco documentada?",
    exec_conclusion=(
        "Foram identificadas {total_threats} ameaças (canónicas + heurísticas activas). "
        "O score máximo observado é {risk_label}. "
        "Esta conclusão é heurística e não substitui testes de segurança ou auditoria."
    ),
    arch_counts="Componentes: {n_comp} · Fluxos: {n_flows} · Fronteiras: {n_tb}.",
    default_threat_action="Tratar ameaça `{threat_id}` conforme controlos sugeridos.",
    ownership_scope="Itens sugeridos para `{role}`",
    owner_pending_display="a definir",
    ownership_explanation="Owner sugerido pelo motor — validar com a governança interna.",
    strategic_baseline_title="Baseline de secure architecture",
    strategic_baseline_detail=(
        "Documentar padrões de fronteiras, identidade e dados sensíveis alinhados ao vosso catálogo."
    ),
    strategic_integrations_title="Política de integrações",
    strategic_integrations_detail=("Definir requisitos mínimos para webhooks, callbacks e integrações third-party."),
    strategic_pack_title="Pack / controlo",
    roadmap_immediate="Imediato",
    roadmap_short="Curto prazo",
    roadmap_medium="Médio prazo",
    tb_delta="Achados de fronteira: {before} → {after}",
    struct_delta="Estruturais: {before} → {after}",
    baseline_narrative=("Delta de score máximo: {delta}; ameaças adicionadas {added}, removidas {removed}."),
    tech_methodology_outputs=(
        "Outputs específicos do engine por metodologia estão em `analysis_json` e em "
        "`methodology_insights` / `ai_system_context` quando aplicável."
    ),
    tech_import_evidence="Texto de importação presente em `import_signals_corpus` no documento canónico.",
    disclaimer_summary=(
        "Ownership, exploitability e impacto de negócio são inferências heurísticas para acelerar decisão. "
        "Não representam auditoria nem garantia de exploração real."
    ),
    disclaimer_b1="Priorização composta (P1/P2/P3) combina score, exposição e esforço estimado.",
    disclaimer_b2="Recomendações estratégicas devem ser validadas contra políticas internas.",
    business_impact_summary=(
        "Principais vectores: confidencialidade, integridade e disponibilidade — ver secção de impacto por ameaça."
    ),
    mq_line="Pré-check {score}/100 ({band}); confiança recomendações: {conf}.",
    mc_line_prefix="Completude metodológica:",
    threat_canonical_prefix="[canónica]",
    wizard_trace="{source_tag} → {effect} ({weight}): {explanation}",
)

_BUILDER_EN = PremiumBuilderCopy(
    status_requires_immediate="Requires immediate attention",
    status_action_recommended="Action recommended",
    status_acceptable_plain="Acceptable with follow-up",
    status_acceptable_no_aggregate="Acceptable with follow-up (no aggregate score)",
    risk_not_calculated="not calculated",
    risk_elevated="elevated",
    risk_high="high",
    risk_medium="medium",
    risk_low_moderate="low to moderate",
    readiness_high="Does the model indicate elevated risk given current heuristics?",
    readiness_moderate="Scores are moderate — validate with testing and business context.",
    readiness_release="Does the system appear release-ready with these open findings?",
    readiness_compensating="Are compensating controls or formal risk acceptance documented?",
    exec_conclusion=(
        "{total_threats} threats were identified (canonical + active heuristics). "
        "The maximum observed score is {risk_label}. "
        "This conclusion is heuristic and does not replace security testing or audits."
    ),
    arch_counts="Components: {n_comp} · Flows: {n_flows} · Trust boundaries: {n_tb}.",
    default_threat_action="Treat threat `{threat_id}` using suggested controls.",
    ownership_scope="Suggested items for `{role}`",
    owner_pending_display="to be defined",
    ownership_explanation="Owner suggested by the engine — validate with internal governance.",
    strategic_baseline_title="Secure architecture baseline",
    strategic_baseline_detail=(
        "Document patterns for boundaries, identity, and sensitive data aligned with your catalog."
    ),
    strategic_integrations_title="Integration policy",
    strategic_integrations_detail=(
        "Define minimum requirements for webhooks, callbacks, and third-party integrations."
    ),
    strategic_pack_title="Pack / control",
    roadmap_immediate="Immediate",
    roadmap_short="Short term",
    roadmap_medium="Medium term",
    tb_delta="Boundary findings: {before} → {after}",
    struct_delta="Structural: {before} → {after}",
    baseline_narrative="Maximum score delta: {delta}; threats added {added}, removed {removed}.",
    tech_methodology_outputs=(
        "Engine outputs per methodology are in `analysis_json` and in "
        "`methodology_insights` / `ai_system_context` when applicable."
    ),
    tech_import_evidence="Import text is present in canonical document `import_signals_corpus`.",
    disclaimer_summary=(
        "Ownership, exploitability, and business impact are heuristic inferences to speed decisions. "
        "They do not represent an audit or guarantee of real-world exploitability."
    ),
    disclaimer_b1="Composite prioritization (P1/P2/P3) combines score, exposure, and estimated effort.",
    disclaimer_b2="Strategic recommendations must be validated against internal policies.",
    business_impact_summary=(
        "Main vectors: confidentiality, integrity, and availability — see per-threat impact section."
    ),
    mq_line="Pre-check {score}/100 ({band}); recommendation confidence: {conf}.",
    mc_line_prefix="Methodology completeness:",
    threat_canonical_prefix="[canonical]",
    wizard_trace="{source_tag} → {effect} ({weight}): {explanation}",
)

_RENDER_PT = PremiumRenderCopy(
    md_em_dash="—",
    md_no_data="_Sem dados._",
    nd="n/d",
    md_executive_cover="## Capa executiva",
    md_schema_version="**Schema / versão documento:**",
    md_primary_methodology="**Metodologia principal:**",
    md_system_sector="**Tipo de sistema / setor:**",
    md_analysis_date="**Data da análise:**",
    md_app_version="**Versão App Suite Modeling:**",
    md_risk_class="**Classificação de risco (heurística):**",
    md_overall_state="**Estado geral:**",
    md_inference_notice="### Aviso de inferência",
    md_executive_summary="## Executive summary",
    md_total_threats="**Total de ameaças (canónicas + heurísticas activas):**",
    md_urgency="**Urgência:**",
    md_exec_conclusion="**Conclusão executiva:**",
    md_sev_distribution="### Distribuição por severidade",
    hdr_severity="Severidade",
    hdr_count="Contagem",
    md_meth_distribution="### Distribuição por metodologia (motor)",
    hdr_methodology="Metodologia",
    hdr_threats="Ameaças",
    md_top_tb="### Principais trust boundaries",
    md_top_surfaces="### Principais superfícies (componentes)",
    md_top5_titles="### Top 5 riscos (título)",
    md_readiness_questions="### Perguntas de readiness",
    md_none_listed="_Nenhuma listada._",
    md_guided_context="## Contexto de decisão (assistente / completude)",
    md_model_quality="**Qualidade do modelo:**",
    md_methodology_line="**Metodologia:**",
    md_wizard_notes="### Notas do assistente",
    md_audit_trail="### Audit trail do assistente (resumo)",
    md_gap_precheck="### Lacunas do pré-check",
    md_anti_patterns="### Anti-padrões",
    md_arch_overview="## Visão arquitetural resumida",
    md_main_components="### Componentes principais",
    md_main_flows="### Fluxos principais",
    md_meth_used_vs_rec="### Metodologia usada vs recomendada",
    md_used="**Usada:**",
    md_recommended="**Recomendada:**",
    md_reason="**Motivo:**",
    md_stats_distribution="## Estatísticas e distribuição",
    hdr_metric="Métrica",
    hdr_value="Valor",
    md_total_threats_metric="Total de ameaças",
    md_by_stride="### Por STRIDE",
    hdr_stride="STRIDE",
    hdr_n="N",
    md_heatmap_stride_sev="### Heatmap STRIDE × severidade (contagens)",
    md_ranking_components="### Ranking de componentes (score agregado heurístico)",
    hdr_component="Componente",
    hdr_score="Score",
    md_top10_risks="## Top 10 riscos prioritários",
    hdr_rank="#",
    hdr_id="ID",
    hdr_title="Título",
    hdr_p="P",
    hdr_tier="Tier",
    hdr_action_short="Acção resumida",
    md_root_cause_groups="## Agrupamento por causa raiz",
    md_occurrences_backlog="**Ocorrências (itens de backlog):**",
    md_single_fix="**Correção única sugerida:**",
    md_controls="**Controlos:**",
    md_exploit_sample="## Contexto de exploração (amostra)",
    md_locality="Localidade:",
    md_external="externo:",
    md_mitm="MITM:",
    md_business_impact_labels="## Impacto de negócio (etiquetas sugeridas)",
    md_quick_wins="## Quick wins",
    md_ownership="## Ownership sugerido (papel lógico)",
    md_to_define="a definir",
    md_items="itens",
    md_strategic="## Recomendações estratégicas",
    md_roadmap="## Roadmap de remediação",
    md_baseline_diff="## Baseline / diff",
    md_new="**Novos:**",
    md_removed="**Removidos:**",
    md_semantic_diff="### Diff semântico (entre execuções de análise)",
    md_semantic_diff_note=(
        "_Heurística sobre pré-check, anti-patterns e ranking — não atribui causa a alterações no YAML._"
    ),
    md_improved="_Melhorou:_",
    md_attention="_Atenção:_",
    md_risk_impact_reading="_Impacto de risco (leitura):_",
    md_dedup="## Deduplicação inteligente",
    md_dedup_ids="— IDs:",
    md_explainability="## Explainability",
    md_technical_appendix="## Apêndice técnico",
    md_threats_excerpt="<details><summary>Ameaças (trecho)</summary>",
    md_appendix_coverage="_A listar {shown} de {total} ameaças._",
    md_appendix_truncated=(
        "_A listagem completa está no bundle de análise (`otm analyze --json-out`, API `POST /v1/analysis`)._"
    ),
    md_methodology_adaptation="## Adaptação por metodologia",
    md_footer="*Gerado pelo App Suite Modeling — report premium.*",
    html_lang="pt-BR",
    html_inference="Inferência.",
    html_exec_summary="Executive summary",
    html_total_threats="Total threats:",
    html_urgency="Urgency:",
    html_top_risks="Top risks",
    html_th_rank="#",
    html_th_id="ID",
    html_th_title="Title",
    html_th_tier="Tier",
    html_th_p="P",
    html_root_causes="Root causes",
    html_roadmap="Roadmap",
    html_baseline="Baseline / diff",
    html_meta_schema="Schema",
    html_meta_methodology="Methodology",
    html_meta_date="Date",
    html_meta_product_version="Product version",
    html_state="State:",
    html_risk_heuristic="Risk (heuristic):",
    html_footer=("Premium report — App Suite Modeling. Full technical content is available in exported Markdown."),
)

_RENDER_EN = PremiumRenderCopy(
    md_em_dash="—",
    md_no_data="_No data._",
    nd="n/a",
    md_executive_cover="## Executive cover",
    md_schema_version="**Schema / document version:**",
    md_primary_methodology="**Primary methodology:**",
    md_system_sector="**System type / sector:**",
    md_analysis_date="**Analysis date:**",
    md_app_version="**App Suite Modeling version:**",
    md_risk_class="**Risk classification (heuristic):**",
    md_overall_state="**Overall state:**",
    md_inference_notice="### Inference notice",
    md_executive_summary="## Executive summary",
    md_total_threats="**Total threats (canonical + active heuristics):**",
    md_urgency="**Urgency:**",
    md_exec_conclusion="**Executive conclusion:**",
    md_sev_distribution="### Distribution by severity",
    hdr_severity="Severity",
    hdr_count="Count",
    md_meth_distribution="### Distribution by methodology (engine)",
    hdr_methodology="Methodology",
    hdr_threats="Threats",
    md_top_tb="### Main trust boundaries",
    md_top_surfaces="### Main surfaces (components)",
    md_top5_titles="### Top 5 risks (title)",
    md_readiness_questions="### Readiness questions",
    md_none_listed="_None listed._",
    md_guided_context="## Decision context (assistant / completeness)",
    md_model_quality="**Model quality:**",
    md_methodology_line="**Methodology:**",
    md_wizard_notes="### Assistant notes",
    md_audit_trail="### Assistant audit trail (summary)",
    md_gap_precheck="### Pre-check gaps",
    md_anti_patterns="### Anti-patterns",
    md_arch_overview="## Architecture overview",
    md_main_components="### Main components",
    md_main_flows="### Main flows",
    md_meth_used_vs_rec="### Methodology used vs recommended",
    md_used="**Used:**",
    md_recommended="**Recommended:**",
    md_reason="**Reason:**",
    md_stats_distribution="## Statistics and distribution",
    hdr_metric="Metric",
    hdr_value="Value",
    md_total_threats_metric="Total threats",
    md_by_stride="### By STRIDE",
    hdr_stride="STRIDE",
    hdr_n="N",
    md_heatmap_stride_sev="### STRIDE × severity heatmap (counts)",
    md_ranking_components="### Component ranking (aggregate heuristic score)",
    hdr_component="Component",
    hdr_score="Score",
    md_top10_risks="## Top 10 prioritized risks",
    hdr_rank="#",
    hdr_id="ID",
    hdr_title="Title",
    hdr_p="P",
    hdr_tier="Tier",
    hdr_action_short="Summary action",
    md_root_cause_groups="## Grouping by root cause",
    md_occurrences_backlog="**Occurrences (backlog items):**",
    md_single_fix="**Suggested single fix:**",
    md_controls="**Controls:**",
    md_exploit_sample="## Exploitability context (sample)",
    md_locality="Locality:",
    md_external="external:",
    md_mitm="MITM:",
    md_business_impact_labels="## Business impact (suggested labels)",
    md_quick_wins="## Quick wins",
    md_ownership="## Suggested ownership (logical role)",
    md_to_define="to be defined",
    md_items="items",
    md_strategic="## Strategic recommendations",
    md_roadmap="## Remediation roadmap",
    md_baseline_diff="## Baseline / diff",
    md_new="**New:**",
    md_removed="**Removed:**",
    md_semantic_diff="### Semantic diff (between analysis runs)",
    md_semantic_diff_note=(
        "_Heuristic on pre-check, anti-patterns, and ranking — does not attribute cause to YAML changes._"
    ),
    md_improved="_Improved:_",
    md_attention="_Attention:_",
    md_risk_impact_reading="_Risk impact (reading):_",
    md_dedup="## Intelligent deduplication",
    md_dedup_ids="— IDs:",
    md_explainability="## Explainability",
    md_technical_appendix="## Technical appendix",
    md_threats_excerpt="<details><summary>Threats (excerpt)</summary>",
    md_appendix_coverage="_Listing {shown} of {total} threats._",
    md_appendix_truncated=(
        "_The complete listing is in the analysis bundle (`otm analyze --json-out`, API `POST /v1/analysis`)._"
    ),
    md_methodology_adaptation="## Methodology adaptation",
    md_footer="*Generated by App Suite Modeling — premium report.*",
    html_lang="en",
    html_inference="Inference.",
    html_exec_summary="Executive summary",
    html_total_threats="Total threats:",
    html_urgency="Urgency:",
    html_top_risks="Top risks",
    html_th_rank="#",
    html_th_id="ID",
    html_th_title="Title",
    html_th_tier="Tier",
    html_th_p="P",
    html_root_causes="Root causes",
    html_roadmap="Roadmap",
    html_baseline="Baseline / diff",
    html_meta_schema="Schema",
    html_meta_methodology="Methodology",
    html_meta_date="Date",
    html_meta_product_version="Product version",
    html_state="State:",
    html_risk_heuristic="Risk (heuristic):",
    html_footer=("Premium report — App Suite Modeling. Full technical content is available in exported Markdown."),
)


def premium_builder_copy(locale: PremiumReportLocale) -> PremiumBuilderCopy:
    return _BUILDER_EN if locale == "en" else _BUILDER_PT


def premium_render_copy(locale: PremiumReportLocale) -> PremiumRenderCopy:
    return _RENDER_EN if locale == "en" else _RENDER_PT


def premium_error_analysis_required(locale: PremiumReportLocale) -> str:
    if locale == "en":
        return "Provide `analysis` or set `run_analysis: true`."
    return "Forneça `analysis` ou defina `run_analysis: true`."
