"""Textos user-facing para `export_analysis_markdown` (pt-BR / en)."""

from __future__ import annotations

from dataclasses import dataclass

from otm_exporters.export_locale import ExportArtifactLocale, normalize_export_locale


@dataclass(frozen=True, slots=True)
class AnalysisMarkdownMessages:
    heading_automatic: str
    bullet_engine: str
    bullet_methodology: str
    bullet_recommendation: str
    bullet_industry_pack: str
    bullet_structural: str
    bullet_trust_boundary: str
    bullet_heuristic_new: str
    bullet_heuristic_covered: str
    bullet_pack_new: str
    bullet_pack_covered: str
    bullet_max_score: str
    framework_agg_title: str
    framework_agg_intro: str
    pack_control_title: str
    section_structural: str
    section_trust_flows: str
    risk_categories_title: str
    risk_categories_blurb: str
    risk_cat_economic: str
    risk_cat_abuse: str
    risk_cat_state: str
    risk_cat_stride: str
    risk_item_in_target: str
    threat_target_label: str
    consolidated_recs_title: str
    rec_webhook: str
    rec_payment: str
    rec_cancel: str
    rec_coupon: str
    rec_auth: str
    ref_none: str
    ref_more: str
    threats_harmonized_title: str
    threats_harmonized_blurb: str
    threats_complete_title: str
    threats_complete_blurb: str
    engine_dedup_notes: str
    threat_line_fw_label: str
    more_entries: str
    harmonization_notes: str
    plot4ai_title: str
    plot_patterns: str
    plot_surfaces: str
    plot_recs: str
    plot_sensitive: str
    plot_layer_group: str
    plot4ai_footer: str
    methodology_insights_title: str
    profile_prefix: str
    exec_summary_title: str
    total_active_line: str
    methodology_applied: str
    immediate_priority: str
    priority_item: str
    scope_general: str
    explain_title: str
    explain_blurb: str
    explain_more: str
    quality_title: str
    precheck_line: str
    completeness_line: str
    wizard_context_title: str
    wizard_context_blurb: str
    audit_title: str
    audit_blurb: str
    audit_entry: str
    model_gaps_title: str
    anti_patterns_title: str
    anti_pattern_confidence: str
    next_steps_title: str
    next_no_high_priority: str
    next_workshop: str
    next_backlog: str
    next_controls: str
    next_use_insights: str
    # `### Consolidação de risco e cockpit executivo` and its bullets were the only user-facing
    # block in this exporter that never took the message bundle: with `locale=en` an entire
    # Portuguese section sat between two English ones in the delivered Markdown.
    aggregate_cockpit_title: str
    agg_active_threats: str
    agg_total_score: str
    agg_mean_max: str
    agg_severity_distribution: str
    agg_top_threats: str
    agg_top_components: str
    agg_top_flows: str
    agg_top_assets: str
    agg_dominant_themes: str
    agg_mitigation_starters: str
    cockpit_posture: str
    cockpit_next_review: str


_MSG: dict[ExportArtifactLocale, AnalysisMarkdownMessages] = {
    "pt-BR": AnalysisMarkdownMessages(
        heading_automatic="## Análise automática (motor)",
        bullet_engine="- Versão do motor:",
        bullet_methodology="- Metodologia:",
        bullet_recommendation="- Recomendação aplicada:",
        bullet_industry_pack="- Industry pack:",
        bullet_structural="- Avisos estruturais:",
        bullet_trust_boundary="- Achados de fronteira:",
        bullet_heuristic_new="- Heurísticas base novas:",
        bullet_heuristic_covered="- Heurísticas base já cobertas:",
        bullet_pack_new="- Ameaças do pack (novas):",
        bullet_pack_covered="- Ameaças do pack (já cobertas):",
        bullet_max_score="- Maior score heurístico (L×I):",
        framework_agg_title="### Referências a frameworks (agregado)",
        framework_agg_intro=("Contagem de referências `framework:control_id` nas heurísticas (por catálogo canónico):"),
        pack_control_title="### Controlo sugerido (pack)",
        section_structural="### Avisos estruturais",
        section_trust_flows="### Fluxos entre fronteiras",
        risk_categories_title="### Categorias de risco (top)",
        risk_categories_blurb=(
            "Bloco curto para leitura humana; a lista completa permanece abaixo (com rastreabilidade no JSON)."
        ),
        risk_cat_economic="Fraude econômica",
        risk_cat_abuse="Abuso de processo / lógica de negócio",
        risk_cat_state="Inconsistência de estado",
        risk_cat_stride="Técnico clássico (STRIDE)",
        risk_item_in_target="em",
        threat_target_label="alvo",
        consolidated_recs_title="### Recomendações consolidadas por causa raiz",
        rec_webhook=(
            "Padronizar idempotência por `event_id/request_id` e bloquear replay "
            "com armazenamento de eventos processados."
        ),
        rec_payment=("Exigir correlação `payment -> owner -> plano -> entitlement` antes de ativação de benefício."),
        rec_cancel=("Aplicar revogação atômica de entitlement no cancelamento com reconciliação periódica de estado."),
        rec_coupon=("Aplicar política anti-abuso de cupom: unicidade por owner/período, anti-stacking e anti-reuso."),
        rec_auth=(
            "Implementar autorização contextual (ownership, vínculo e escopo econômico), além de autenticação técnica."
        ),
        ref_none="—",
        ref_more="… (+{n})",
        threats_harmonized_title="### Ameaças sugeridas (harmonizadas)",
        threats_harmonized_blurb=(
            "Visualização priorizada por especificidade (`biz_*`) com redução de redundância semântica."
        ),
        threats_complete_title="### Ameaças sugeridas (lista completa)",
        threats_complete_blurb=(
            "Visualização sem redução de redundância: todos os achados activos, ordenados por especificidade (`biz_*`)."
        ),
        engine_dedup_notes=(
            "- **De-duplicação do motor:** {skipped} achados foram marcados como duplicados "
            "e não entram em nenhuma vista deste relatório "
            "(presentes no JSON com `skipped_as_duplicate`)."
        ),
        threat_line_fw_label="Frameworks",
        more_entries="\n… e mais {n} entradas.",
        harmonization_notes=(
            "\nNotas de harmonização: {suppressed} "
            "achados STRIDE genéricos foram ocultados nesta visão "
            "por sobreposição com achados específicos `biz_*` "
            "(rastreáveis no JSON)."
        ),
        plot4ai_title="### PLOT4ai — relatório de contexto IA",
        plot_patterns="- **Padrões (heurístico):**",
        plot_surfaces="- **Superfícies de risco:**",
        plot_recs="- **Recomendações prioritárias:**",
        plot_sensitive="- **Dados sensíveis / contexto:**",
        plot_layer_group="- **Agrupamento por camada (`plot4ai_*`):**",
        plot4ai_footer=(
            "Interpretação: sinais derivam do texto e da estrutura do modelo OTM — "
            "validar sempre com arquitectura e artefactos reais."
        ),
        methodology_insights_title="### Insights metodológicos",
        profile_prefix="- Perfil:",
        exec_summary_title="### Resumo executivo",
        total_active_line=("- Total de ameaças ativas: **{active}** · Maior score: **{max_score}**"),
        methodology_applied="- Metodologia aplicada:",
        immediate_priority="- Prioridade imediata:",
        priority_item="  - {title} (score {score}) {prep} `{tgt}`",
        scope_general="escopo geral",
        explain_title="### Explicabilidade (resumo)",
        explain_blurb=(
            "Motivos estruturados gerados pelo motor (metodologia, achados, risco). "
            "Detalhe completo no JSON do resultado."
        ),
        explain_more="\n… e mais {n} entradas no JSON.",
        quality_title="### Qualidade do modelo e metodologia (resumo)",
        precheck_line=(
            "- **Pré-check:** score **{score}/100** (banda `{band}`) · "
            "confiança nas recomendações: `{conf}` · fit STRIDE: `{fit}`."
        ),
        completeness_line="- **Completude metodológica:** `{state}` — {reasons}{note}",
        wizard_context_title="### Contexto do assistente (modelação guiada)",
        wizard_context_blurb=("Notas derivadas de respostas `wz:` alinhadas ao perfil semântico do modelo."),
        audit_title="### Rastreabilidade do assistente (audit trail)",
        audit_blurb=(
            "Ligação compacta entre declarações no questionário e efeitos no motor (ranking, corpus, observações)."
        ),
        audit_entry=("- `{tag}` — **{effect}** ({weight}; {mechanism}) → {areas}: {explanation}"),
        model_gaps_title="### Lacunas do modelo (pré-check)",
        anti_patterns_title="### Anti-padrões de modelagem (destaque)",
        anti_pattern_confidence=" · confiança _{conf}_ — ",
        next_steps_title="### Próximos passos sugeridos",
        next_no_high_priority="- Sem ameaças ativas de alta prioridade nesta execução.",
        next_workshop="- Validar os 3 maiores riscos em workshop curto com engenharia e segurança.",
        next_backlog="- Converter os achados críticos em backlog com owner e prazo.",
        next_controls=("- Revisar controles de acesso, integridade de fluxo e proteção de dados sensíveis."),
        next_use_insights=("- Usar os insights do perfil **{profile}** para priorização contextual."),
        aggregate_cockpit_title="### Consolidação de risco e cockpit executivo",
        agg_active_threats="Ameaças activas",
        agg_total_score="Score total",
        agg_mean_max="Média / máx",
        agg_severity_distribution="Distribuição por severidade",
        agg_top_threats="Top ameaças (score)",
        agg_top_components="Componentes mais críticos",
        agg_top_flows="Fluxos mais críticos",
        agg_top_assets="Ativos mais críticos",
        agg_dominant_themes="Temas dominantes",
        agg_mitigation_starters="Mitigação inicial",
        cockpit_posture="Postura",
        cockpit_next_review="Rever",
    ),
    "en": AnalysisMarkdownMessages(
        heading_automatic="## Automated analysis (engine)",
        bullet_engine="- Engine version:",
        bullet_methodology="- Methodology:",
        bullet_recommendation="- Recommendation applied:",
        bullet_industry_pack="- Industry pack:",
        bullet_structural="- Structural warnings:",
        bullet_trust_boundary="- Trust-boundary findings:",
        bullet_heuristic_new="- New base heuristics:",
        bullet_heuristic_covered="- Base heuristics already covered:",
        bullet_pack_new="- Pack threats (new):",
        bullet_pack_covered="- Pack threats (already covered):",
        bullet_max_score="- Highest heuristic score (L×I):",
        framework_agg_title="### Framework references (aggregate)",
        framework_agg_intro=("Count of `framework:control_id` references in heuristics (by canonical catalog):"),
        pack_control_title="### Suggested controls (pack)",
        section_structural="### Structural warnings",
        section_trust_flows="### Flows across boundaries",
        risk_categories_title="### Risk categories (top)",
        risk_categories_blurb=("Short block for human reading; the full list remains below (traceable in JSON)."),
        risk_cat_economic="Economic fraud",
        risk_cat_abuse="Process abuse / business logic",
        risk_cat_state="State inconsistency",
        risk_cat_stride="Classic technical (STRIDE)",
        risk_item_in_target="in",
        threat_target_label="target",
        consolidated_recs_title="### Consolidated root-cause recommendations",
        rec_webhook=(
            "Standardize idempotency via `event_id/request_id` and block replay with storage of processed events."
        ),
        rec_payment=("Require correlation `payment -> owner -> plan -> entitlement` before activating benefits."),
        rec_cancel=("Apply atomic entitlement revocation on cancellation with periodic state reconciliation."),
        rec_coupon=("Apply anti-abuse coupon policy: uniqueness per owner/period, anti-stacking, anti-reuse."),
        rec_auth=(
            "Implement contextual authorization (ownership, linkage, economic scope) beyond technical authentication."
        ),
        ref_none="—",
        ref_more="… (+{n})",
        threats_harmonized_title="### Suggested threats (harmonized)",
        threats_harmonized_blurb=("View prioritized by specificity (`biz_*`) with reduced semantic redundancy."),
        threats_complete_title="### Suggested threats (complete list)",
        threats_complete_blurb=(
            "View without redundancy reduction: every active finding, ordered by specificity (`biz_*`)."
        ),
        engine_dedup_notes=(
            "- **Engine de-duplication:** {skipped} findings were marked as duplicates and appear "
            "in no view of this report (present in the JSON with `skipped_as_duplicate`)."
        ),
        threat_line_fw_label="Frameworks",
        more_entries="\n… and {n} more entries.",
        harmonization_notes=(
            "\nHarmonization notes: {suppressed} generic STRIDE findings were hidden in this view "
            "due to overlap with specific `biz_*` findings (traceable in JSON)."
        ),
        plot4ai_title="### PLOT4ai — AI context report",
        plot_patterns="- **Patterns (heuristic):**",
        plot_surfaces="- **Risk surfaces:**",
        plot_recs="- **Priority recommendations:**",
        plot_sensitive="- **Sensitive data / context:**",
        plot_layer_group="- **Grouping by layer (`plot4ai_*`):**",
        plot4ai_footer=(
            "Interpretation: signals are derived from OTM model text and structure — "
            "always validate with architecture and real artifacts."
        ),
        methodology_insights_title="### Methodology insights",
        profile_prefix="- Profile:",
        exec_summary_title="### Executive summary",
        total_active_line="- Active threats: **{active}** · Highest score: **{max_score}**",
        methodology_applied="- Methodology applied:",
        immediate_priority="- Immediate priority:",
        priority_item="  - {title} (score {score}) {prep} `{tgt}`",
        scope_general="general scope",
        explain_title="### Explainability (summary)",
        explain_blurb=(
            "Structured reasons from the engine (methodology, findings, risk). Full detail in the result JSON."
        ),
        explain_more="\n… and {n} more entries in JSON.",
        quality_title="### Model and methodology quality (summary)",
        precheck_line=(
            "- **Pre-check:** score **{score}/100** (band `{band}`) · "
            "recommendation confidence: `{conf}` · STRIDE fit: `{fit}`."
        ),
        completeness_line="- **Methodology completeness:** `{state}` — {reasons}{note}",
        wizard_context_title="### Wizard context (guided modeling)",
        wizard_context_blurb="Notes derived from `wz:` answers aligned with the model semantic profile.",
        audit_title="### Wizard traceability (audit trail)",
        audit_blurb=("Compact link between questionnaire statements and engine effects (ranking, corpus, notes)."),
        audit_entry="- `{tag}` — **{effect}** ({weight}; {mechanism}) → {areas}: {explanation}",
        model_gaps_title="### Model gaps (pre-check)",
        anti_patterns_title="### Modeling anti-patterns (highlight)",
        anti_pattern_confidence=" · confidence _{conf}_ — ",
        next_steps_title="### Suggested next steps",
        next_no_high_priority="- No high-priority active threats in this run.",
        next_workshop="- Validate the top 3 risks in a short workshop with engineering and security.",
        next_backlog="- Turn critical findings into backlog items with owner and deadline.",
        next_controls="- Review access controls, flow integrity, and sensitive-data protection.",
        next_use_insights="- Use profile insights **{profile}** for contextual prioritization.",
        aggregate_cockpit_title="### Risk consolidation and executive cockpit",
        agg_active_threats="Active threats",
        agg_total_score="Total score",
        agg_mean_max="Mean / max",
        agg_severity_distribution="Severity distribution",
        agg_top_threats="Top threats (score)",
        agg_top_components="Most critical components",
        agg_top_flows="Most critical flows",
        agg_top_assets="Most critical assets",
        agg_dominant_themes="Dominant themes",
        agg_mitigation_starters="Initial mitigation",
        cockpit_posture="Posture",
        cockpit_next_review="Review",
    ),
}


def analysis_markdown_messages(locale: str | None) -> AnalysisMarkdownMessages:
    return _MSG[normalize_export_locale(locale)]


def risk_category_key(h) -> str:
    """Chave estável para bucketização (independente do idioma do relatório)."""
    t = f"{h.id} {h.title} {h.description}".lower()
    if h.id.startswith("biz_") or any(k in t for k in ("business_abuse", "economic_fraud", "state_inconsistency")):
        if any(
            k in t
            for k in (
                "economic_fraud",
                "coupon",
                "cupom",
                "discount",
                "billing",
                "entitlement",
                "premium",
            )
        ):
            return "economic"
        if "state_inconsistency" in t or any(k in t for k in ("out_of_order", "regression", "inconsist", "cancel")):
            return "state"
        return "abuse"
    return "stride"


def risk_category_title(key: str, msgs: AnalysisMarkdownMessages) -> str:
    return {
        "economic": msgs.risk_cat_economic,
        "abuse": msgs.risk_cat_abuse,
        "state": msgs.risk_cat_state,
        "stride": msgs.risk_cat_stride,
    }[key]
