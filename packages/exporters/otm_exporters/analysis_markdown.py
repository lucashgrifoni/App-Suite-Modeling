"""
Secção Markdown do resultado de análise (motor) — reutilizável por API e relatórios.

Snapshots / modo harmonizado / ordem de secções: `tests/test_exporters.py` (`analysis_markdown`).
"""

from __future__ import annotations

import os

from otm_core_schema import FrameworkRef, ThreatModelDocument
from otm_framework_mappings import framework_display_name
from otm_threat_engine import AnalysisResult


def _target_of(h) -> str:
    return h.target_component_id or h.target_data_flow_id or "—"


def _active_threats(result: AnalysisResult) -> list:
    return [h for h in result.heuristic_threats if not h.skipped_as_duplicate]


def _is_business_specific(h) -> bool:
    t = f"{h.id} {h.title}".lower()
    return h.id.startswith("biz_") or any(
        k in t for k in ("business_abuse", "economic_fraud", "state_inconsistency")
    )


def _biz_family_flags(active: list) -> dict[str, bool]:
    ids = " ".join(h.id.lower() for h in active if _is_business_specific(h))
    return {
        "webhook": "biz_webhook_" in ids,
        "coupon": "biz_coupon_" in ids,
        "payment_entitlement": "biz_payment_entitlement_" in ids,
        "authorization": "biz_authorization_" in ids,
        "balance": "biz_balance_" in ids,
        "cancel": "biz_cancel_" in ids,
    }


def _cluster_token_hit(*, h, tokens: tuple[str, ...]) -> bool:
    t = f"{h.id} {h.title} {_target_of(h)}".lower()
    return any(tok in t for tok in tokens)


def _cluster_suppressible(*, h, flags: dict[str, bool]) -> bool:
    """
    Supressão somente de apresentação: reduz STRIDE genérico quando `biz_*` cobre a causa raiz.

    Regras intencionais:
    - Conservadoras: só suprimem STRIDE em `tampering`/`elevation_of_privilege`.
    - Semânticas controladas por "famílias" (webhook, coupon, entitlement, authorization,
      balance, cancel).
    """
    if _is_business_specific(h):
        return False

    if h.stride.value not in {"tampering", "elevation_of_privilege"}:
        return False

    # Cluster Webhook / Payment gateway / replay / idempotência / ordem de eventos
    if flags.get("webhook") and _cluster_token_hit(
        h=h,
        tokens=(
            "webhook",
            "gateway_webhook",
            "payment_gateway",
            "payment provider webhook",
            "payment_webhook_provider",
        ),
    ):
        return True

    # Cluster Cupom / desconto / stacking
    if flags.get("coupon") and _cluster_token_hit(
        h=h,
        tokens=(
            "coupon",
            "cupom",
            "desconto",
            "discount",
            "checkout_coupon",
            "coupon_store",
        ),
    ):
        return True

    # Cluster Entitlement / billing mismatch / ativação indevida / owner mismatch
    if flags.get("payment_entitlement") and _cluster_token_hit(
        h=h,
        tokens=(
            "entitlement",
            "subscription",
            "billing",
            "premium",
            "plan",
            "cancel",
            "revog",
            "subscription_service",
            "entitlement_service",
        ),
    ):
        return True

    # Cluster Authorization contextual (negócio / ownership / vínculo)
    if flags.get("authorization") and _cluster_token_hit(
        h=h, tokens=("authorization", "autoriz", "ownership", "vinculo", "vínculo")
    ):
        return True

    # Cluster Saldo / ledger / consistência econômica
    if flags.get("balance") and _cluster_token_hit(
        h=h,
        tokens=(
            "balance",
            "saldo",
            "ledger",
            "transactions",
            "transacoes",
            "ledger_service",
        ),
    ):
        return True

    # Cluster Cancelamento / revogação / inconsistencia de estado
    if flags.get("cancel") and _cluster_token_hit(
        h=h,
        tokens=("cancel", "revog", "subscription"),
    ):
        return True

    return False


def _priority_score(h) -> float:
    base = h.risk.score or 0.0
    if _is_business_specific(h):
        return base + 3.0
    return base


def _markdown_view_mode() -> str:
    """
    Controle para comparação before/after sem alterar o JSON.
    - legacy: sem supressão (apresenta tudo)
    - harmonized: supressão conservadora + categorias top-N
    """
    mode = (os.environ.get("OTM_MARKDOWN_VIEW_MODE") or "harmonized").strip().lower()
    return mode if mode in {"legacy", "harmonized"} else "harmonized"


def _build_harmonized(active: list) -> tuple[list, int, dict[str, int]]:
    """Prioriza especificidade e reduz redundância sem perder rastreabilidade no output."""
    mode = _markdown_view_mode()
    if mode == "legacy":
        return sorted(active, key=_priority_score, reverse=True), 0, {}

    flags = _biz_family_flags(active)
    harmonized: list = []
    suppressed = 0
    suppressed_by_cluster: dict[str, int] = {
        "cluster_root_cause_overlap": 0,
    }
    for h in sorted(active, key=_priority_score, reverse=True):
        if _cluster_suppressible(h=h, flags=flags):
            suppressed += 1
            suppressed_by_cluster["cluster_root_cause_overlap"] += 1
            continue
        harmonized.append(h)
    return harmonized, suppressed, suppressed_by_cluster


def _risk_category(h) -> str:
    """Categorias funcionais (curtas) para coesão narrativa no Markdown."""
    t = f"{h.id} {h.title} {h.description}".lower()
    if _is_business_specific(h):
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
            return "Fraude econômica"
        if "state_inconsistency" in t or any(
            k in t for k in ("out_of_order", "regression", "inconsist", "cancel")
        ):
            return "Inconsistência de estado"
        return "Abuso de processo / lógica de negócio"
    return "Técnico clássico (STRIDE)"


def _append_risk_categories_block(lines: list[str], harmonized: list, *, top_n: int = 2) -> None:
    if _markdown_view_mode() != "harmonized":
        return
    if not harmonized:
        return
    cats = [
        "Fraude econômica",
        "Abuso de processo / lógica de negócio",
        "Inconsistência de estado",
        "Técnico clássico (STRIDE)",
    ]
    buckets: dict[str, list] = {c: [] for c in cats}
    for h in sorted(harmonized, key=_priority_score, reverse=True):
        c = _risk_category(h)
        if c in buckets and len(buckets[c]) < top_n:
            buckets[c].append(h)
    if not any(buckets[c] for c in cats):
        return
    lines.append("### Categorias de risco (top)")
    lines.append("")
    lines.append(
        "Bloco curto para leitura humana; a lista completa permanece abaixo "
        "(com rastreabilidade no JSON)."
    )
    lines.append("")
    for c in cats:
        items = buckets[c]
        if not items:
            continue
        lines.append(f"#### {c}")
        lines.append("")
        for h in items:
            tgt = _target_of(h)
            sc = h.risk.score if h.risk.score is not None else "—"
            lines.append(f"- {h.title} (`{h.id}`) em `{tgt}` — score {sc}")
        lines.append("")


def _append_root_cause_recommendations(lines: list[str], active: list) -> None:
    text = " ".join(f"{h.id} {h.title} {h.description}".lower() for h in active)
    recs: list[str] = []
    if any(k in text for k in ("webhook", "replay", "idempot")):
        recs.append(
            "Padronizar idempotência por `event_id/request_id` e bloquear replay "
            "com armazenamento de eventos processados."
        )
    if any(k in text for k in ("owner", "entitlement", "payment")):
        recs.append(
            "Exigir correlação `payment -> owner -> plano -> entitlement` antes de ativação "
            "de benefício."
        )
    if any(k in text for k in ("cancel", "revoga", "revog")):
        recs.append(
            "Aplicar revogação atômica de entitlement no cancelamento com reconciliação "
            "periódica de estado."
        )
    if any(k in text for k in ("coupon", "cupom", "discount", "desconto")):
        recs.append(
            "Aplicar política anti-abuso de cupom: unicidade por owner/período, "
            "anti-stacking e anti-reuso."
        )
    if any(k in text for k in ("authorization", "autorizacao", "ownership", "vínculo", "vinculo")):
        recs.append(
            "Implementar autorização contextual (ownership, vínculo e escopo econômico), "
            "além de autenticação técnica."
        )
    if not recs:
        return
    lines.append("### Recomendações consolidadas por causa raiz")
    lines.append("")
    for r in recs:
        lines.append(f"- {r}")
    lines.append("")


def _format_framework_refs_compact(refs: list[FrameworkRef], *, max_items: int = 8) -> str:
    if not refs:
        return "—"
    parts = [f"`{r.framework}:{r.control_id}`" for r in refs[:max_items]]
    if len(refs) > max_items:
        parts.append(f"… (+{len(refs) - max_items})")
    return ", ".join(parts)


def _append_framework_aggregate(lines: list[str], result: AnalysisResult) -> None:
    s = result.summary
    if not s.framework_ref_counts_by_catalog:
        return
    lines.append("")
    lines.append("### Referências a frameworks (agregado)")
    lines.append("")
    lines.append(
        "Contagem de referências `framework:control_id` nas heurísticas (por catálogo canónico):"
    )
    lines.append("")
    for fw, n in sorted(s.framework_ref_counts_by_catalog.items()):
        label = framework_display_name(fw)
        lines.append(f"- **{label}** (`{fw}`): {n}")
    lines.append("")


def _append_heuristic_block(
    lines: list[str],
    harmonized: list,
    *,
    suppressed: int,
    max_heuristic_rows: int,
) -> None:
    if not harmonized:
        return
    lines.append("### Ameaças sugeridas (harmonizadas)")
    lines.append("")
    lines.append(
        "Visualização priorizada por especificidade (`biz_*`) com redução de redundância semântica."
    )
    lines.append("")
    for h in harmonized[:max_heuristic_rows]:
        tgt = _target_of(h)
        sc = h.risk.score if h.risk.score is not None else "—"
        refs = _format_framework_refs_compact(h.framework_refs)
        lines.append(
            f"- **{h.title}** (`{h.id}`) → alvo `{tgt}` — score {sc}  \n  - Frameworks: {refs}"
        )
    if len(harmonized) > max_heuristic_rows:
        lines.append(f"\n… e mais {len(harmonized) - max_heuristic_rows} entradas.")
    if suppressed > 0:
        lines.append(
            f"\nNotas de harmonização: {suppressed} "
            "achados STRIDE genéricos foram ocultados nesta visão "
            "por sobreposição com achados específicos `biz_*` "
            "(rastreáveis no JSON)."
        )
    lines.append("")


def _append_plot4ai_ai_context_block(lines: list[str], result: AnalysisResult) -> None:
    ctx = result.ai_system_context
    if result.methodology.value != "plot4ai" or ctx is None:
        return
    lines.append("### PLOT4ai — relatório de contexto IA")
    lines.append("")
    lines.append(ctx.synopsis)
    lines.append("")
    if ctx.pattern_tags:
        lines.append(f"- **Padrões (heurístico):** {', '.join(ctx.pattern_tags)}")
    if ctx.primary_risk_surfaces:
        lines.append("- **Superfícies de risco:**")
        for p in ctx.primary_risk_surfaces[:6]:
            lines.append(f"  - {p}")
    if ctx.prioritized_recommendations:
        lines.append("- **Recomendações prioritárias:**")
        for rec in ctx.prioritized_recommendations[:7]:
            lines.append(f"  - {rec}")
    if ctx.sensitive_data_notes:
        lines.append("- **Dados sensíveis / contexto:**")
        for n in ctx.sensitive_data_notes[:5]:
            lines.append(f"  - {n}")
    if ctx.heuristic_ids_by_layer:
        lines.append("- **Agrupamento por camada (`plot4ai_*`):**")
        for lid, hid in list(ctx.heuristic_ids_by_layer.items())[:10]:
            preview = ", ".join(hid[:5])
            tail = "…" if len(hid) > 5 else ""
            lines.append(f"  - `{lid}`: {preview}{tail}")
    lines.append("")
    lines.append(
        "Interpretação: sinais derivam do texto e da estrutura do modelo OTM — "
        "validar sempre com arquitectura e artefactos reais."
    )
    lines.append("")


def _append_methodology_insights_block(lines: list[str], result: AnalysisResult) -> None:
    insights = result.methodology_insights
    if not insights or not insights.blocks:
        return
    lines.append("### Insights metodológicos")
    lines.append("")
    if insights.profile:
        lines.append(f"- Perfil: **{insights.profile}**")
        lines.append("")
    for b in insights.blocks:
        lines.append(f"#### {b.title}")
        lines.append("")
        for item in b.items:
            lines.append(f"- {item}")
        lines.append("")


def _append_executive_summary_from_harmonized(
    lines: list[str],
    result: AnalysisResult,
    *,
    active: list,
    harmonized: list,
) -> None:
    s = result.summary
    top = sorted(harmonized, key=_priority_score, reverse=True)[:3]
    lines.append("### Resumo executivo")
    lines.append("")
    lines.append(
        f"- Total de ameaças ativas: **{len(active)}** · "
        f"Maior score: **{s.max_risk_score if s.max_risk_score is not None else '—'}**"
    )
    lines.append(f"- Metodologia aplicada: **{result.methodology.value}**")
    if top:
        lines.append("- Prioridade imediata:")
        for h in top:
            tgt = _target_of(h) or "escopo geral"
            lines.append(f"  - {h.title} (score {h.risk.score}) em `{tgt}`")
    lines.append("")


def _append_explainability_compact(lines: list[str], result: AnalysisResult, *, max_items: int = 12) -> None:
    """Secção curta: não duplica o JSON completo de `explanations`."""
    if not result.explanations:
        return
    lines.append("### Explicabilidade (resumo)")
    lines.append("")
    lines.append(
        "Motivos estruturados gerados pelo motor (metodologia, achados, risco). "
        "Detalhe completo no JSON do resultado."
    )
    lines.append("")
    for ex in result.explanations[:max_items]:
        cat = getattr(ex.category, "value", ex.category)
        typ = getattr(ex.type, "value", ex.type)
        lines.append(f"- **[{typ}/{cat}]** {ex.subject} — {ex.message}")
    if len(result.explanations) > max_items:
        lines.append(f"\n… e mais {len(result.explanations) - max_items} entradas no JSON.")
    lines.append("")


def _append_guided_context_and_audit(lines: list[str], result: AnalysisResult) -> None:
    """Propaga notas do assistente, audit trail, lacunas do pré-check e anti-padrões (fora da UI)."""
    pq = result.model_quality_precheck
    mc = result.methodology_completeness
    if pq is not None or mc is not None:
        lines.append("### Qualidade do modelo e metodologia (resumo)")
        lines.append("")
        if pq is not None:
            lines.append(
                f"- **Pré-check:** score **{pq.score_0_100}/100** (banda `{pq.band}`) · "
                f"confiança nas recomendações: `{pq.recommendation_confidence}` · "
                f"fit STRIDE: `{pq.methodology_fit_matrix.get('stride', pq.methodology_fit)}`."
            )
        if mc is not None:
            reasons = "; ".join(mc.reasons[:3]) if mc.reasons else "—"
            note = mc.note or ""
            lines.append(
                f"- **Completude metodológica:** `{mc.state.value}` — {reasons}"
                + (f" · _{note}_" if note else "")
            )
        lines.append("")

    if result.wizard_context_notes:
        lines.append("### Contexto do assistente (modelação guiada)")
        lines.append("")
        lines.append("Notas derivadas de respostas `wz:` alinhadas ao perfil semântico do modelo.")
        lines.append("")
        for note in result.wizard_context_notes[:8]:
            lines.append(f"- {note}")
        lines.append("")

    if result.wizard_signal_trace:
        lines.append("### Rastreabilidade do assistente (audit trail)")
        lines.append("")
        lines.append(
            "Ligação compacta entre declarações no questionário e efeitos no motor (ranking, corpus, observações)."
        )
        lines.append("")
        for entry in result.wizard_signal_trace[:12]:
            areas = ", ".join(entry.impact_areas) if entry.impact_areas else "—"
            lines.append(
                f"- `{entry.source_tag}` — **{entry.effect}** ({entry.weight}; {entry.mechanism}) → "
                f"{areas}: {entry.explanation}"
            )
        lines.append("")

    if pq and pq.checks:
        failed = [c for c in pq.checks if not c.passed][:6]
        if failed:
            lines.append("### Lacunas do modelo (pré-check)")
            lines.append("")
            for c in failed:
                lines.append(f"- [{c.code}] {c.message}")
            lines.append("")

    if result.anti_pattern_hits:
        lines.append("### Anti-padrões de modelagem (destaque)")
        lines.append("")
        for hit in result.anti_pattern_hits[:10]:
            conf = getattr(hit, "confidence_hint", None) or "medium"
            lines.append(f"- **{hit.name}** (`{hit.id}`) · confiança _{conf}_ — {hit.message}")
        lines.append("")


def _append_next_steps_from_harmonized(
    lines: list[str],
    result: AnalysisResult,
    *,
    harmonized: list,
) -> None:
    top = sorted(harmonized, key=_priority_score, reverse=True)[:5]
    lines.append("### Próximos passos sugeridos")
    lines.append("")
    if not top:
        lines.append("- Sem ameaças ativas de alta prioridade nesta execução.")
        lines.append("")
        return
    lines.append("- Validar os 3 maiores riscos em workshop curto com engenharia e segurança.")
    lines.append("- Converter os achados críticos em backlog com owner e prazo.")
    lines.append(
        "- Revisar controles de acesso, integridade de fluxo e proteção de dados sensíveis."
    )
    _append_root_cause_recommendations(lines, top)
    if result.methodology_insights and result.methodology_insights.profile:
        lines.append(
            f"- Usar os insights do perfil **{result.methodology_insights.profile}** "
            "para priorização contextual."
        )
    lines.append("")


def export_analysis_markdown(result: AnalysisResult, *, max_heuristic_rows: int = 50) -> str:
    """
    Relatório da análise heurística: totais, frameworks, achados e ameaças sugeridas.
    Não inclui o documento canónico — use `export_document_and_analysis_markdown`
    para o pacote completo.
    """
    s = result.summary
    lines: list[str] = [
        "## Análise automática (motor)",
        "",
        f"- Versão do motor: `{result.engine_version}`",
        f"- Metodologia: `{result.methodology.value}`",
    ]
    if result.methodology_recommendation_reason:
        lines.append(f"- Recomendação aplicada: {result.methodology_recommendation_reason}")
    if result.industry_pack_id:
        lines.append(f"- Industry pack: `{result.industry_pack_id}`")
    lines.extend(
        [
            f"- Avisos estruturais: {s.structural_findings}",
            f"- Achados de fronteira: {s.trust_boundary_findings}",
            f"- Heurísticas base novas: {s.heuristic_threats_generated}",
            f"- Heurísticas base já cobertas: {s.heuristic_threats_skipped_duplicate}",
            f"- Ameaças do pack (novas): {s.pack_threats_generated}",
            f"- Ameaças do pack (já cobertas): {s.pack_threats_skipped_duplicate}",
        ]
    )
    if s.max_risk_score is not None:
        lines.append(f"- Maior score heurístico (L×I): **{s.max_risk_score}**")
    _append_framework_aggregate(lines, result)
    lines.append("")
    if result.pack_control_hints:
        lines.append("### Controlo sugerido (pack)")
        lines.append("")
        for hint in result.pack_control_hints:
            lines.append(f"- {hint}")
        lines.append("")
    if result.structural_findings:
        lines.append("### Avisos estruturais")
        lines.append("")
        for f in result.structural_findings:
            lines.append(f"- [{f.severity}] {f.message}")
        lines.append("")
    if result.trust_boundary_findings:
        lines.append("### Fluxos entre fronteiras")
        lines.append("")
        for f in result.trust_boundary_findings:
            lines.append(f"- {f.message}")
        lines.append("")
    _append_guided_context_and_audit(lines, result)
    active = _active_threats(result)
    harmonized, suppressed, _ = _build_harmonized(active)
    _append_executive_summary_from_harmonized(lines, result, active=active, harmonized=harmonized)
    _append_methodology_insights_block(lines, result)
    _append_plot4ai_ai_context_block(lines, result)
    _append_risk_categories_block(lines, harmonized, top_n=2)
    _append_heuristic_block(
        lines,
        harmonized,
        suppressed=suppressed,
        max_heuristic_rows=max_heuristic_rows,
    )
    _append_explainability_compact(lines, result)
    _append_next_steps_from_harmonized(lines, result, harmonized=harmonized)
    return "\n".join(lines)


def export_document_and_analysis_markdown(
    doc: ThreatModelDocument,
    result: AnalysisResult,
) -> str:
    """Concatena Markdown do documento e da análise (atalho para relatórios)."""
    from otm_exporters.document_markdown import export_document_markdown

    return export_document_markdown(doc) + "\n" + export_analysis_markdown(result)
