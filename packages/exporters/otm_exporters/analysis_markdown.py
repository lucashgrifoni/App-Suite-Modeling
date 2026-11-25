"""
Secção Markdown do resultado de análise (motor) — reutilizável por API e relatórios.

Snapshots / modo harmonizado / ordem de secções: `tests/test_exporters.py` (`analysis_markdown`).
"""

from __future__ import annotations

import os
from typing import Any

from otm_core_schema import FrameworkRef, ThreatModelDocument
from otm_framework_mappings import framework_display_name
from otm_threat_engine import AnalysisResult

from otm_exporters.analysis_markdown_i18n import (
    AnalysisMarkdownMessages,
    analysis_markdown_messages,
    risk_category_key,
    risk_category_title,
)
from otm_exporters.markdown_text import md_code, md_inline


def _target_of(h) -> str:
    return h.target_component_id or h.target_data_flow_id or "—"


def _active_threats(result: AnalysisResult) -> list:
    return [h for h in result.heuristic_threats if not h.skipped_as_duplicate]


def _is_business_specific(h) -> bool:
    t = f"{h.id} {h.title}".lower()
    return h.id.startswith("biz_") or any(k in t for k in ("business_abuse", "economic_fraud", "state_inconsistency"))


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

    - `legacy`: sem a redução de redundância **deste exportador** — apresenta todos os achados
      activos, sem categorias top-N.
    - `harmonized` (predefinição): supressão conservadora + categorias top-N.

    O que `legacy` **não** faz, apesar de a docstring anterior prometer "apresenta tudo": repor os
    achados que o motor já marcou `skipped_as_duplicate` antes de o exportador correr. Esses estão
    fora de ambas as vistas e só voltam com `OTM_ENGINE_STRIDE_NOISE_SUPPRESSION=0`; quantos são é
    agora dito no resumo executivo, em vez de o leitor ter de descobrir pelo JSON.
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
            continue  # pragma: no cover - defensive guard
        harmonized.append(h)
    return harmonized, suppressed, suppressed_by_cluster


def _append_risk_categories_block(
    lines: list[str],
    harmonized: list,
    *,
    top_n: int,
    msgs: AnalysisMarkdownMessages,
) -> None:
    if _markdown_view_mode() != "harmonized":
        return
    if not harmonized:
        return
    order = ("economic", "abuse", "state", "stride")
    buckets: dict[str, list] = {k: [] for k in order}
    for h in sorted(harmonized, key=_priority_score, reverse=True):
        k = risk_category_key(h)
        if k in buckets and len(buckets[k]) < top_n:
            buckets[k].append(h)
    if not any(buckets[k] for k in order):  # noqa: E501  # pragma: no cover - risk_category_key always maps to a bucket
        return
    lines.append(msgs.risk_categories_title)
    lines.append("")
    lines.append(msgs.risk_categories_blurb)
    lines.append("")
    for key in order:
        items = buckets[key]
        if not items:
            continue
        lines.append(f"#### {risk_category_title(key, msgs)}")
        lines.append("")
        for h in items:
            tgt = _target_of(h)
            sc = h.risk.score if h.risk.score is not None else "—"
            lines.append(f"- {md_inline(h.title)} (`{h.id}`) {msgs.risk_item_in_target} `{tgt}` — score {sc}")
        lines.append("")


def _append_root_cause_recommendations(
    lines: list[str],
    active: list,
    msgs: AnalysisMarkdownMessages,
) -> None:
    text = " ".join(f"{h.id} {h.title} {h.description}".lower() for h in active)
    recs: list[str] = []
    if any(k in text for k in ("webhook", "replay", "idempot")):
        recs.append(msgs.rec_webhook)
    if any(k in text for k in ("owner", "entitlement", "payment")):
        recs.append(msgs.rec_payment)
    if any(k in text for k in ("cancel", "revoga", "revog")):
        recs.append(msgs.rec_cancel)
    if any(k in text for k in ("coupon", "cupom", "discount", "desconto")):
        recs.append(msgs.rec_coupon)
    if any(k in text for k in ("authorization", "autorizacao", "ownership", "vínculo", "vinculo")):
        recs.append(msgs.rec_auth)
    if not recs:
        return
    lines.append(msgs.consolidated_recs_title)
    lines.append("")
    for r in recs:
        lines.append(f"- {r}")
    lines.append("")


def _format_framework_refs_compact(
    refs: list[FrameworkRef],
    msgs: AnalysisMarkdownMessages,
    *,
    max_items: int = 8,
) -> str:
    if not refs:
        return msgs.ref_none
    # `md_code` e não crases à mão: o `control_id` de uma regra personalizada é texto livre do
    # utilizador, e uma crase nele fechava o span e devolvia o controlo do Markdown ao ficheiro
    # de regras. Este era o único sink deste ficheiro que ainda recebia o valor cru.
    parts = [md_code(f"{r.framework}:{r.control_id}") for r in refs[:max_items]]
    if len(refs) > max_items:
        parts.append(msgs.ref_more.format(n=len(refs) - max_items))
    return ", ".join(parts)


def _append_framework_aggregate(
    lines: list[str],
    result: AnalysisResult,
    msgs: AnalysisMarkdownMessages,
) -> None:
    s = result.summary
    if not s.framework_ref_counts_by_catalog:
        return
    lines.append("")
    lines.append(msgs.framework_agg_title)
    lines.append("")
    lines.append(msgs.framework_agg_intro)
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
    msgs: AnalysisMarkdownMessages,
) -> None:
    if not harmonized:
        return
    # The heading described the harmonized view even when the harmonized view was not what got
    # rendered: `OTM_MARKDOWN_VIEW_MODE=legacy` printed "(harmonizadas)" over the complete,
    # unreduced list, so a reader holding the report could not tell which of the two they had.
    complete = _markdown_view_mode() == "legacy"
    lines.append(msgs.threats_complete_title if complete else msgs.threats_harmonized_title)
    lines.append("")
    lines.append(msgs.threats_complete_blurb if complete else msgs.threats_harmonized_blurb)
    lines.append("")
    for h in harmonized[:max_heuristic_rows]:
        tgt = _target_of(h)
        sc = h.risk.score if h.risk.score is not None else "—"
        refs = _format_framework_refs_compact(h.framework_refs, msgs)
        lines.append(
            f"- **{md_inline(h.title)}** (`{h.id}`) → {msgs.threat_target_label} `{tgt}` — score {sc}  \n"
            f"  - {msgs.threat_line_fw_label}: {refs}"
        )
    if len(harmonized) > max_heuristic_rows:
        lines.append(msgs.more_entries.format(n=len(harmonized) - max_heuristic_rows))
    if suppressed > 0:
        lines.append(msgs.harmonization_notes.format(suppressed=suppressed))
    lines.append("")


def _append_bullet_section(lines: list[str], header: str, items: list[str], limit: int) -> None:
    """Emite um cabeçalho seguido de bullets (até `limit`) quando há itens."""
    if not items:
        return
    lines.append(header)
    for item in items[:limit]:
        lines.append(f"  - {md_inline(item)}")


def _append_plot4ai_ai_context_block(
    lines: list[str],
    result: AnalysisResult,
    msgs: AnalysisMarkdownMessages,
) -> None:
    ctx = result.ai_system_context
    if result.methodology.value != "plot4ai" or ctx is None:
        return
    lines.append(msgs.plot4ai_title)
    lines.append("")
    lines.append(md_inline(ctx.synopsis))
    lines.append("")
    if ctx.pattern_tags:
        lines.append(f"{msgs.plot_patterns} {md_inline(', '.join(ctx.pattern_tags))}")
    _append_bullet_section(lines, msgs.plot_surfaces, ctx.primary_risk_surfaces, 6)
    _append_bullet_section(lines, msgs.plot_recs, ctx.prioritized_recommendations, 7)
    _append_bullet_section(lines, msgs.plot_sensitive, ctx.sensitive_data_notes, 5)
    if ctx.heuristic_ids_by_layer:
        lines.append(msgs.plot_layer_group)
        for lid, hid in list(ctx.heuristic_ids_by_layer.items())[:10]:
            preview = ", ".join(hid[:5])
            tail = "…" if len(hid) > 5 else ""
            lines.append(f"  - `{lid}`: {preview}{tail}")
    lines.append("")
    lines.append(msgs.plot4ai_footer)
    lines.append("")


def _append_methodology_insights_block(
    lines: list[str],
    result: AnalysisResult,
    msgs: AnalysisMarkdownMessages,
) -> None:
    insights = result.methodology_insights
    if not insights or not insights.blocks:
        return
    lines.append(msgs.methodology_insights_title)
    lines.append("")
    if insights.profile:
        lines.append(f"{msgs.profile_prefix} **{md_inline(insights.profile)}**")
        lines.append("")
    for b in insights.blocks:
        lines.append(f"#### {md_inline(b.title)}")
        lines.append("")
        for item in b.items:
            lines.append(f"- {md_inline(item)}")
        lines.append("")


def _append_executive_summary_from_harmonized(
    lines: list[str],
    result: AnalysisResult,
    *,
    active: list,
    harmonized: list,
    msgs: AnalysisMarkdownMessages,
) -> None:
    s = result.summary
    top = sorted(harmonized, key=_priority_score, reverse=True)[:3]
    lines.append(msgs.exec_summary_title)
    lines.append("")
    lines.append(
        msgs.total_active_line.format(
            active=len(active),
            max_score=s.max_risk_score if s.max_risk_score is not None else "—",
        )
    )
    # "Active" was accurate but incomplete: the engine had already withheld findings as duplicates
    # before this exporter saw them, and the report said nowhere how many. A reader comparing the
    # report against `otm analyze --json-out` found nine findings unaccounted for.
    withheld = len(result.heuristic_threats) - len(active)
    if withheld > 0:
        lines.append(msgs.engine_dedup_notes.format(skipped=withheld))
    lines.append(f"{msgs.methodology_applied} **{result.methodology.value}**")
    if top:
        lines.append(msgs.immediate_priority)
        for h in top:
            tgt = _target_of(h) or msgs.scope_general
            lines.append(
                msgs.priority_item.format(
                    title=md_inline(h.title),
                    score=h.risk.score,
                    tgt=tgt,
                    prep=msgs.risk_item_in_target,
                )
            )
    lines.append("")


def _append_explainability_compact(
    lines: list[str],
    result: AnalysisResult,
    *,
    max_items: int,
    msgs: AnalysisMarkdownMessages,
) -> None:
    """Secção curta: não duplica o JSON completo de `explanations`."""
    if not result.explanations:
        return
    lines.append(msgs.explain_title)
    lines.append("")
    lines.append(msgs.explain_blurb)
    lines.append("")
    for ex in result.explanations[:max_items]:
        cat = getattr(ex.category, "value", ex.category)
        typ = getattr(ex.type, "value", ex.type)
        lines.append(f"- **[{typ}/{cat}]** {md_inline(ex.subject)} — {md_inline(ex.message)}")
    if len(result.explanations) > max_items:
        lines.append(msgs.explain_more.format(n=len(result.explanations) - max_items))
    lines.append("")


def _append_quality_block(lines: list[str], result: AnalysisResult, msgs: AnalysisMarkdownMessages) -> None:
    pq = result.model_quality_precheck
    mc = result.methodology_completeness
    if pq is None and mc is None:
        return
    lines.append(msgs.quality_title)
    lines.append("")
    if pq is not None:
        lines.append(
            msgs.precheck_line.format(
                score=pq.score_0_100,
                band=pq.band,
                conf=pq.recommendation_confidence,
                fit=pq.methodology_fit_matrix.get("stride", pq.methodology_fit),
            )
        )
    if mc is not None:
        reasons = md_inline("; ".join(mc.reasons[:3])) if mc.reasons else "—"
        note = md_inline(mc.note or "")
        note_suffix = f" · _{note}_" if note else ""
        lines.append(msgs.completeness_line.format(state=mc.state.value, reasons=reasons, note=note_suffix))
    lines.append("")


def _append_wizard_context_block(lines: list[str], result: AnalysisResult, msgs: AnalysisMarkdownMessages) -> None:
    if not result.wizard_context_notes:
        return
    lines.append(msgs.wizard_context_title)
    lines.append("")
    lines.append(msgs.wizard_context_blurb)
    lines.append("")
    for note in result.wizard_context_notes[:8]:
        lines.append(f"- {md_inline(note)}")
    lines.append("")


def _append_audit_trail_block(lines: list[str], result: AnalysisResult, msgs: AnalysisMarkdownMessages) -> None:
    if not result.wizard_signal_trace:
        return
    lines.append(msgs.audit_title)
    lines.append("")
    lines.append(msgs.audit_blurb)
    lines.append("")
    for entry in result.wizard_signal_trace[:12]:
        areas = ", ".join(entry.impact_areas) if entry.impact_areas else "—"
        lines.append(
            msgs.audit_entry.format(
                tag=md_inline(entry.source_tag),
                effect=md_inline(entry.effect),
                weight=entry.weight,
                mechanism=md_inline(entry.mechanism),
                areas=md_inline(areas),
                explanation=md_inline(entry.explanation),
            )
        )
    lines.append("")


def _append_model_gaps_block(lines: list[str], result: AnalysisResult, msgs: AnalysisMarkdownMessages) -> None:
    pq = result.model_quality_precheck
    if not (pq and pq.checks):
        return
    failed = [c for c in pq.checks if not c.passed][:6]
    if not failed:
        return
    lines.append(msgs.model_gaps_title)
    lines.append("")
    for c in failed:
        lines.append(f"- [{md_inline(c.code)}] {md_inline(c.message)}")
    lines.append("")


def _append_anti_patterns_block(lines: list[str], result: AnalysisResult, msgs: AnalysisMarkdownMessages) -> None:
    if not result.anti_pattern_hits:
        return
    lines.append(msgs.anti_patterns_title)
    lines.append("")
    for hit in result.anti_pattern_hits[:10]:
        conf = getattr(hit, "confidence_hint", None) or "medium"
        lines.append(
            f"- **{md_inline(hit.name)}** (`{hit.id}`)"
            f"{msgs.anti_pattern_confidence.format(conf=md_inline(conf))}{md_inline(hit.message)}"
        )
    lines.append("")


def _append_guided_context_and_audit(
    lines: list[str],
    result: AnalysisResult,
    msgs: AnalysisMarkdownMessages,
) -> None:
    """Propaga notas do assistente, audit trail, lacunas do pré-check e anti-padrões (fora da UI)."""
    _append_quality_block(lines, result, msgs)
    _append_wizard_context_block(lines, result, msgs)
    _append_audit_trail_block(lines, result, msgs)
    _append_model_gaps_block(lines, result, msgs)
    _append_anti_patterns_block(lines, result, msgs)


def _append_top_groups(lines: list[str], ar: dict[str, Any], msgs: AnalysisMarkdownMessages) -> None:
    for label, key in (
        (msgs.agg_top_components, "top_components"),
        (msgs.agg_top_flows, "top_flows"),
        (msgs.agg_top_assets, "top_assets"),
    ):
        items = ar.get(key) or []
        if items:
            lines.append(
                f"- **{label}:** "
                + ", ".join(f"`{md_inline(x.get('id'))}` ({x.get('aggregate_score')})" for x in items[:4])
            )


def _format_severity_distribution(dist: dict[str, Any]) -> str:
    """`high: 13, medium: 3` — the raw `dict` used to be interpolated, so the delivered report
    carried a Python repr, quotes and all: ``{'high': 13, 'medium': 3}``."""
    return ", ".join(f"{band}: {count}" for band, count in dist.items())


def _append_aggregate_block(lines: list[str], ar: dict[str, Any], msgs: AnalysisMarkdownMessages) -> None:
    lines.append(
        f"- **{msgs.agg_active_threats}:** {ar.get('active_threat_count', '—')} · "
        f"**{msgs.agg_total_score}:** {ar.get('total_risk_score', '—')} · "
        f"**{msgs.agg_mean_max}:** {ar.get('mean_risk_score', '—')} / {ar.get('max_risk_score', '—')}"
    )
    dist = ar.get("severity_distribution") or {}
    if dist:
        lines.append(f"- **{msgs.agg_severity_distribution}:** {_format_severity_distribution(dist)}")
    top_t = ar.get("top_threats") or []
    if top_t:
        lines.append(f"- **{msgs.agg_top_threats}:**")
        for row in top_t[:5]:
            lines.append(
                f"  - `{md_inline(row.get('id'))}` — {md_inline(row.get('title', ''))[:80]} (score {row.get('score')})"
            )
    _append_top_groups(lines, ar, msgs)
    themes = ar.get("dominant_themes") or []
    if themes:
        lines.append(f"- **{msgs.agg_dominant_themes}:** " + "; ".join(md_inline(t) for t in themes[:6]))
    starters = ar.get("mitigation_starters") or []
    if starters:
        lines.append(f"- **{msgs.agg_mitigation_starters}:**")
        for st in starters[:6]:
            lines.append(f"  - {md_inline(st)}")


def _append_cockpit_block(lines: list[str], dc: dict[str, Any], msgs: AnalysisMarkdownMessages) -> None:
    lines.append(
        f"- **{msgs.cockpit_posture}:** `{md_inline(dc.get('risk_posture', '—'))}` — "
        f"{md_inline(dc.get('headline', ''))}"
    )
    for kd in dc.get("key_decisions") or []:
        lines.append(f"  - {md_inline(kd)}")
    for nr in (dc.get("next_reviews") or [])[:4]:
        lines.append(f"  - *{msgs.cockpit_next_review}:* {md_inline(nr)}")


def _append_aggregate_risk_and_cockpit(
    lines: list[str], result: AnalysisResult, msgs: AnalysisMarkdownMessages
) -> None:
    """Bloco compacto de consolidação agregada e cockpit executivo (JSON em AnalysisResult)."""
    ar = result.aggregate_risk
    dc = result.decision_cockpit
    if not ar and not dc:
        return
    lines.append(msgs.aggregate_cockpit_title)
    lines.append("")
    if ar:
        _append_aggregate_block(lines, ar, msgs)
    if dc:
        _append_cockpit_block(lines, dc, msgs)
    lines.append("")


def _append_next_steps_from_harmonized(
    lines: list[str],
    result: AnalysisResult,
    *,
    harmonized: list,
    msgs: AnalysisMarkdownMessages,
) -> None:
    top = sorted(harmonized, key=_priority_score, reverse=True)[:5]
    lines.append(msgs.next_steps_title)
    lines.append("")
    if not top:
        lines.append(msgs.next_no_high_priority)
        lines.append("")
        return
    lines.append(msgs.next_workshop)
    lines.append(msgs.next_backlog)
    lines.append(msgs.next_controls)
    _append_root_cause_recommendations(lines, top, msgs)
    if result.methodology_insights and result.methodology_insights.profile:
        lines.append(msgs.next_use_insights.format(profile=result.methodology_insights.profile))
    lines.append("")


def export_analysis_markdown(
    result: AnalysisResult,
    *,
    max_heuristic_rows: int = 50,
    locale: str | None = None,
) -> str:
    """
    Relatório da análise heurística: totais, frameworks, achados e ameaças sugeridas.
    Não inclui o documento canónico — use `export_document_and_analysis_markdown`
    para o pacote completo.
    """
    msgs = analysis_markdown_messages(locale)
    s = result.summary
    lines: list[str] = [
        msgs.heading_automatic,
        "",
        f"{msgs.bullet_engine} `{result.engine_version}`",
        f"{msgs.bullet_methodology} `{result.methodology.value}`",
    ]
    if result.methodology_recommendation_reason:
        lines.append(f"{msgs.bullet_recommendation} {md_inline(result.methodology_recommendation_reason)}")
    if result.industry_pack_id:
        lines.append(f"{msgs.bullet_industry_pack} `{result.industry_pack_id}`")
    lines.extend(
        [
            f"{msgs.bullet_structural} {s.structural_findings}",
            f"{msgs.bullet_trust_boundary} {s.trust_boundary_findings}",
            f"{msgs.bullet_heuristic_new} {s.heuristic_threats_generated}",
            f"{msgs.bullet_heuristic_covered} {s.heuristic_threats_skipped_duplicate}",
            f"{msgs.bullet_pack_new} {s.pack_threats_generated}",
            f"{msgs.bullet_pack_covered} {s.pack_threats_skipped_duplicate}",
        ]
    )
    if s.max_risk_score is not None:
        lines.append(f"{msgs.bullet_max_score} **{s.max_risk_score}**")
    _append_framework_aggregate(lines, result, msgs)
    _append_aggregate_risk_and_cockpit(lines, result, msgs)
    lines.append("")
    if result.pack_control_hints:
        lines.append(msgs.pack_control_title)
        lines.append("")
        for hint in result.pack_control_hints:
            lines.append(f"- {md_inline(hint)}")
        lines.append("")
    if result.structural_findings:
        lines.append(msgs.section_structural)
        lines.append("")
        for f in result.structural_findings:
            lines.append(f"- [{f.severity}] {md_inline(f.message)}")
        lines.append("")
    if result.trust_boundary_findings:
        lines.append(msgs.section_trust_flows)
        lines.append("")
        for tbf in result.trust_boundary_findings:
            lines.append(f"- {md_inline(tbf.message)}")
        lines.append("")
    _append_guided_context_and_audit(lines, result, msgs)
    active = _active_threats(result)
    harmonized, suppressed, _ = _build_harmonized(active)
    _append_executive_summary_from_harmonized(lines, result, active=active, harmonized=harmonized, msgs=msgs)
    _append_methodology_insights_block(lines, result, msgs)
    _append_plot4ai_ai_context_block(lines, result, msgs)
    _append_risk_categories_block(lines, harmonized, top_n=2, msgs=msgs)
    _append_heuristic_block(
        lines,
        harmonized,
        suppressed=suppressed,
        max_heuristic_rows=max_heuristic_rows,
        msgs=msgs,
    )
    _append_explainability_compact(lines, result, max_items=12, msgs=msgs)
    _append_next_steps_from_harmonized(lines, result, harmonized=harmonized, msgs=msgs)
    return "\n".join(lines)


def export_document_and_analysis_markdown(
    doc: ThreatModelDocument,
    result: AnalysisResult,
    *,
    locale: str | None = None,
) -> str:
    """Concatena Markdown do documento e da análise (atalho para relatórios)."""
    from otm_exporters.document_markdown import export_document_markdown

    return export_document_markdown(doc, locale=locale) + "\n" + export_analysis_markdown(result, locale=locale)
