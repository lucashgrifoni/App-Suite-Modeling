"""Renderização Markdown do payload premium — um único caminho para CLI/API."""

from __future__ import annotations

from .enums import ReportLevel
from .models import PremiumReportPayload
from .report_i18n import premium_render_copy


def _md_table(headers: list[str], rows: list[list[str]], empty_msg: str) -> str:
    if not rows:
        return f"{empty_msg}\n"
    h = "| " + " | ".join(headers) + " |\n"
    sep = "| " + " | ".join("---" for _ in headers) + " |\n"
    body = "".join("| " + " | ".join(row) + " |\n" for row in rows)
    return h + sep + body


def render_premium_markdown(payload: PremiumReportPayload) -> str:
    """Gera Markdown completo; profundidade controlada por `payload.level`."""
    r = premium_render_copy(payload.locale)
    lvl = payload.level
    lines: list[str] = []

    lines.append(f"# {payload.cover.title}\n")
    lines.append(f"{r.md_executive_cover}\n")
    ver = payload.cover.document_version or r.nd
    lines.append(f"- {r.md_schema_version} {payload.cover.schema_version} / {ver}")
    lines.append(f"- {r.md_primary_methodology} {payload.cover.primary_methodology}")
    lines.append(
        f"- {r.md_system_sector} {payload.cover.system_type} · {payload.cover.industry_sector}"
    )
    lines.append(f"- {r.md_analysis_date} {payload.cover.analysis_date_iso}")
    lines.append(f"- {r.md_app_version} {payload.cover.app_suite_version}")
    lines.append(f"- {r.md_risk_class} {payload.cover.overall_risk_label}")
    lines.append(f"- {r.md_overall_state} {payload.cover.overall_status_display}\n")

    lines.append(f"{r.md_inference_notice}\n")
    lines.append(payload.disclaimer.summary)
    for b in payload.disclaimer.bullets:
        lines.append(f"- {b}")
    lines.append("")

    lines.append(f"{r.md_executive_summary}\n")
    es = payload.executive_summary
    lines.append(f"- {r.md_total_threats} {es.threat_count}")
    lines.append(f"- {r.md_urgency} {es.urgency_level}")
    lines.append(f"- {r.md_exec_conclusion} {es.executive_conclusion}\n")
    lines.append(f"{r.md_sev_distribution}\n")
    lines.append(
        _md_table(
            [r.hdr_severity, r.hdr_count],
            [[k, str(v)] for k, v in es.severity_distribution.items()],
            r.md_no_data,
        )
    )
    lines.append(f"{r.md_meth_distribution}\n")
    lines.append(
        _md_table(
            [r.hdr_methodology, r.hdr_threats],
            [[k, str(v)] for k, v in es.methodology_distribution.items()],
            r.md_no_data,
        )
    )
    lines.append(f"{r.md_top_tb}\n")
    lines.append("\n".join(f"- {x}" for x in es.top_trust_boundaries) or r.md_none_listed)
    lines.append(f"\n{r.md_top_surfaces}\n")
    lines.append("\n".join(f"- {x}" for x in es.top_attack_surfaces) or r.md_none_listed)
    lines.append(f"\n{r.md_top5_titles}\n")
    for t in es.top5_risk_titles:
        lines.append(f"- {t}")
    lines.append(f"\n{r.md_readiness_questions}\n")
    for q in es.readiness_questions:
        lines.append(f"- {q}")
    lines.append("")

    if payload.guided_modeling_audit:
        g = payload.guided_modeling_audit
        lines.append(f"{r.md_guided_context}\n")
        if g.model_quality_summary_line:
            lines.append(f"- {r.md_model_quality} {g.model_quality_summary_line}\n")
        if g.methodology_completeness_line:
            lines.append(f"- {r.md_methodology_line} {g.methodology_completeness_line}\n")
        if g.wizard_context_notes:
            lines.append(f"{r.md_wizard_notes}\n")
            for n in g.wizard_context_notes:
                lines.append(f"- {n}")
            lines.append("")
        if g.wizard_signal_trace_lines:
            lines.append(f"{r.md_audit_trail}\n")
            for t in g.wizard_signal_trace_lines:
                lines.append(f"- {t}")
            lines.append("")
        if g.top_model_gap_messages:
            lines.append(f"{r.md_gap_precheck}\n")
            for m in g.top_model_gap_messages:
                lines.append(f"- {m}")
            lines.append("")
        if g.anti_pattern_summaries:
            lines.append(f"{r.md_anti_patterns}\n")
            for a in g.anti_pattern_summaries:
                lines.append(f"- {a}")
            lines.append("")

    if lvl != ReportLevel.EXECUTIVE:
        lines.append(f"{r.md_arch_overview}\n")
        ar = payload.architecture
        lines.append(ar.narrative + "\n")
        lines.append(f"{r.md_main_components}\n")
        lines.append("\n".join(f"- {c}" for c in ar.main_components[:15]))
        lines.append(f"\n{r.md_main_flows}\n")
        lines.append("\n".join(f"- {f}" for f in ar.main_flows[:15]))
        lines.append(f"\n{r.md_meth_used_vs_rec}\n")
        lines.append(f"- {r.md_used} {ar.methodology_used}")
        lines.append(f"- {r.md_recommended} {ar.methodology_recommended or r.nd}")
        if ar.recommendation_reason:
            lines.append(f"- {r.md_reason} {ar.recommendation_reason}")
        lines.append("")

    if lvl != ReportLevel.EXECUTIVE:
        lines.append(f"{r.md_stats_distribution}\n")
        d = payload.distributions
        lines.append(
            _md_table(
                [r.hdr_metric, r.hdr_value],
                [[r.md_total_threats_metric, str(d.total_threats)]],
                r.md_no_data,
            )
        )
        lines.append(f"{r.md_by_stride}\n")
        lines.append(
            _md_table(
                [r.hdr_stride, r.hdr_n],
                [[k, str(v)] for k, v in d.by_stride.items()],
                r.md_no_data,
            )
        )
        lines.append(f"{r.md_heatmap_stride_sev}\n")
        for sk, row in d.heatmap_stride_severity.items():
            lines.append(f"**{sk}:** " + ", ".join(f"{bk}={bv}" for bk, bv in row.items()))
        lines.append(f"\n{r.md_ranking_components}\n")
        lines.append(
            _md_table(
                [r.hdr_component, r.hdr_score],
                [[str(a), f"{b:.3f}"] for a, b in d.top_components_ranked[:10]],
                r.md_no_data,
            )
        )
        lines.append("")

    lines.append(f"{r.md_top10_risks}\n")
    lines.append(
        _md_table(
            [r.hdr_rank, r.hdr_id, r.hdr_title, r.hdr_p, r.hdr_tier, r.hdr_action_short],
            [
                [
                    str(rk.rank),
                    rk.threat_id,
                    rk.title[:80],
                    f"{rk.composite_score:.2f}",
                    rk.priority_tier,
                    rk.recommended_action[:120].replace("|", "/"),
                ]
                for rk in payload.top_risks
            ],
            r.md_no_data,
        )
    )
    lines.append("")

    if lvl != ReportLevel.EXECUTIVE:
        lines.append(f"{r.md_root_cause_groups}\n")
        for g in payload.root_cause_groups[:15]:
            lines.append(f"### {g.display_name} (`{g.key}`)\n")
            lines.append(f"- {r.md_occurrences_backlog} {g.threat_count}")
            lines.append(f"- {r.md_single_fix} {g.single_fix_recommendation[:400]}")
            lines.append(f"- {r.md_controls} {', '.join(g.suggested_controls)}\n")

        lines.append(f"{r.md_exploit_sample}\n")
        for ex in payload.exploitability_profiles[:10]:
            lines.append(f"### {ex.threat_id}\n")
            lines.append(f"- {ex.notes}")
            lines.append(
                f"- {r.md_locality} {ex.attack_locality} · {r.md_external} {ex.requires_external_access} · "
                f"{r.md_mitm} {ex.requires_mitm}\n"
            )

        lines.append(f"{r.md_business_impact_labels}\n")
        for b in payload.business_impacts[:10]:
            lines.append(f"- **{b.threat_id}:** {', '.join(b.labels)} — _{b.rationale}_\n")

    if lvl != ReportLevel.EXECUTIVE:
        lines.append(f"{r.md_quick_wins}\n")
        for qw in payload.quick_wins:
            lines.append(f"- **{qw.title}** (`{qw.backlog_item_id}`): {qw.rationale[:300]}\n")

        lines.append(f"{r.md_ownership}\n")
        for ow in payload.ownership:
            role = ow.suggested_owner_role or r.md_to_define
            lines.append(
                f"- **{role}:** {len(ow.backlog_item_ids)} {r.md_items} {r.md_em_dash} {ow.explanation}\n"
            )

        lines.append(f"{r.md_strategic}\n")
        for s in payload.strategic_recommendations:
            lines.append(f"### {s.title}\n{s.detail}\n")

    lines.append(f"{r.md_roadmap}\n")
    for ph in payload.roadmap:
        lines.append(f"### {ph.title}\n")
        for it in ph.items:
            lines.append(f"- {it}")
        lines.append("")

    if payload.baseline_diff and payload.baseline_diff.has_baseline:
        lines.append(f"{r.md_baseline_diff}\n")
        lines.append(payload.baseline_diff.narrative + "\n")
        lines.append(f"{r.md_new} {', '.join(payload.baseline_diff.threats_added[:20])}\n")
        lines.append(f"{r.md_removed} {', '.join(payload.baseline_diff.threats_removed[:20])}\n")
        bd = payload.baseline_diff
        if (
            bd.semantic_insights_from_analysis
            or bd.semantic_improved
            or bd.semantic_worsened
            or bd.semantic_risk_impact
        ):
            lines.append(f"\n{r.md_semantic_diff}\n")
            lines.append(f"{r.md_semantic_diff_note}\n")
            for x in bd.semantic_insights_from_analysis[:10]:
                lines.append(f"- {x}")
            if bd.semantic_improved:
                lines.append(f"\n{r.md_improved}")
                for x in bd.semantic_improved[:8]:
                    lines.append(f"- {x}")
            if bd.semantic_worsened:
                lines.append(f"\n{r.md_attention}")
                for x in bd.semantic_worsened[:8]:
                    lines.append(f"- {x}")
            if bd.semantic_risk_impact:
                lines.append(f"\n{r.md_risk_impact_reading}")
                for x in bd.semantic_risk_impact[:6]:
                    lines.append(f"- {x}")
            lines.append("")

    if lvl != ReportLevel.EXECUTIVE and payload.deduplication:
        lines.append(f"{r.md_dedup}\n")
        for dg in payload.deduplication[:10]:
            lines.append(
                f"- **{dg.group_key}** ({dg.occurrence_count}x): {dg.unified_remediation[:200]} "
                f"{r.md_dedup_ids} {', '.join(dg.threat_ids[:8])}\n"
            )

    if lvl != ReportLevel.EXECUTIVE:
        lines.append(f"{r.md_explainability}\n")
        for ex in payload.explainability[:20]:
            lines.append(f"- **[{ex.category}]** {ex.message[:400]}\n")

    if lvl == ReportLevel.DEEP and payload.technical_appendix:
        lines.append(f"{r.md_technical_appendix}\n")
        lines.append(payload.technical_appendix.methodology_outputs_note + "\n")
        if payload.technical_appendix.import_evidence_note:
            lines.append(payload.technical_appendix.import_evidence_note + "\n")
        lines.append(f"{r.md_threats_excerpt}\n\n")
        lines.append(payload.technical_appendix.full_threat_listing[:20000])
        lines.append("\n</details>\n")

    if payload.methodology_voice:
        lines.append(f"{r.md_methodology_adaptation}\n")
        for v in payload.methodology_voice:
            lines.append(f"- {v}")
        lines.append("")

    lines.append(f"---\n{r.md_footer}\n")
    return "\n".join(lines)
