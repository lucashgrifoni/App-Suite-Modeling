"""Renderização Markdown do payload premium — um único caminho para CLI/API."""

from __future__ import annotations

from typing import Any

from otm_exporters.markdown_text import md_block, md_inline
from pydantic import BaseModel

from .enums import ReportLevel
from .models import ArchitectureSummary, PremiumReportPayload, TechnicalAppendix, count_appendix_entries
from .report_i18n import PremiumRenderCopy, premium_render_copy

#: Campos que o **builder** já entrega como Markdown pronto (estrutura escrita pelo produto, não
#: valores colocados dentro de uma linha): a listagem do apêndice técnico e o diagrama Mermaid.
#: Achatá-los destruiria o contorno que o próprio renderizador conta emitir, por isso o texto do
#: modelo que entra neles é neutralizado onde é construído (`builder._build_tech_appendix`).
_PREBUILT_MARKDOWN_FIELDS = frozenset(
    {
        (TechnicalAppendix, "full_threat_listing"),
        (ArchitectureSummary, "mermaid_flowchart"),
    }
)


def _inlined(value: Any) -> Any:
    """Cópia do valor com todo o texto achatado a uma linha, recursivamente.

    O contorno do relatório (títulos, listas, tabelas) é decisão deste renderizador; o documento é
    dados do utilizador. Um nome de componente com `\\n\\n## Conclusion\\n\\nNo risks were found.`
    fechava o bullet onde estava e passava a emitir um H2 verdadeiro seguido de um parágrafo — num
    relatório de segurança entregue a um revisor, sete vezes no mesmo ficheiro. A defesa existia
    nos exportadores (`otm_exporters.markdown_text`) e nas células de tabela daqui; faltava em
    tudo o resto.

    É feita **uma vez, à entrada**, e não em cada interpolação: o payload tem ~40 campos de texto
    espalhados por doze secções, e a garantia tem de valer também para o campo que alguém
    acrescentar amanhã. Só as exceções acima ficam de fora, explicitamente.
    """
    if isinstance(value, str):
        return md_inline(value)
    if isinstance(value, BaseModel):
        cls = type(value)
        return value.model_copy(
            update={
                name: (
                    getattr(value, name) if (cls, name) in _PREBUILT_MARKDOWN_FIELDS else _inlined(getattr(value, name))
                )
                for name in cls.model_fields
            }
        )
    if isinstance(value, dict):
        return {_inlined(k): _inlined(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return tuple(_inlined(v) for v in value)
    if isinstance(value, list):
        return [_inlined(v) for v in value]
    return value


def _md_cell(value: str) -> str:
    """Escape a value for safe use inside a Markdown table cell.

    Attacker-controlled fields (component names, threat titles) can contain a
    pipe — which would add columns — or a line break — which would split one
    logical row across physical lines. Escape the pipe and flatten line breaks
    so the table structure stays intact.
    """
    text = value.replace("\r", " ").replace("\n", " ")
    return text.replace("\\", "\\\\").replace("|", "\\|")


def _md_table(headers: list[str], rows: list[list[str]], empty_msg: str) -> str:
    if not rows:
        return f"{empty_msg}\n"
    h = "| " + " | ".join(_md_cell(x) for x in headers) + " |\n"
    sep = "| " + " | ".join("---" for _ in headers) + " |\n"
    body = "".join("| " + " | ".join(_md_cell(c) for c in row) + " |\n" for row in rows)
    return h + sep + body


def _md_cover_and_disclaimer(lines: list[str], payload: PremiumReportPayload, r: PremiumRenderCopy) -> None:
    lines.append(f"# {payload.cover.title}\n")
    lines.append(f"{r.md_executive_cover}\n")
    ver = payload.cover.document_version or r.nd
    lines.append(f"- {r.md_schema_version} {payload.cover.schema_version} / {ver}")
    lines.append(f"- {r.md_primary_methodology} {payload.cover.primary_methodology}")
    lines.append(f"- {r.md_system_sector} {payload.cover.system_type} · {payload.cover.industry_sector}")
    lines.append(f"- {r.md_analysis_date} {payload.cover.analysis_date_iso}")
    lines.append(f"- {r.md_app_version} {payload.cover.app_suite_version}")
    lines.append(f"- {r.md_risk_class} {payload.cover.overall_risk_label}")
    lines.append(f"- {r.md_overall_state} {payload.cover.overall_status_display}\n")

    lines.append(f"{r.md_inference_notice}\n")
    lines.append(md_block(payload.disclaimer.summary))
    for bullet in payload.disclaimer.bullets:
        lines.append(f"- {bullet}")
    lines.append("")


def _md_executive_summary(lines: list[str], payload: PremiumReportPayload, r: PremiumRenderCopy) -> None:
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
    lines.append("\n".join(f"- {md_block(x)}" for x in es.top_trust_boundaries) or r.md_none_listed)
    lines.append(f"\n{r.md_top_surfaces}\n")
    lines.append("\n".join(f"- {md_block(x)}" for x in es.top_attack_surfaces) or r.md_none_listed)
    lines.append(f"\n{r.md_top5_titles}\n")
    for t in es.top5_risk_titles:
        lines.append(f"- {md_block(t)}")
    lines.append(f"\n{r.md_readiness_questions}\n")
    for q in es.readiness_questions:
        lines.append(f"- {q}")
    lines.append("")


def _md_guided_audit(lines: list[str], payload: PremiumReportPayload, r: PremiumRenderCopy) -> None:
    if not payload.guided_modeling_audit:
        return
    audit = payload.guided_modeling_audit
    lines.append(f"{r.md_guided_context}\n")
    if audit.model_quality_summary_line:
        lines.append(f"- {r.md_model_quality} {audit.model_quality_summary_line}\n")
    if audit.methodology_completeness_line:
        lines.append(f"- {r.md_methodology_line} {audit.methodology_completeness_line}\n")
    if audit.wizard_context_notes:
        lines.append(f"{r.md_wizard_notes}\n")
        for n in audit.wizard_context_notes:
            lines.append(f"- {n}")
        lines.append("")
    if audit.wizard_signal_trace_lines:
        lines.append(f"{r.md_audit_trail}\n")
        for trace_line in audit.wizard_signal_trace_lines:
            lines.append(f"- {trace_line}")
        lines.append("")
    if audit.top_model_gap_messages:
        lines.append(f"{r.md_gap_precheck}\n")
        for m in audit.top_model_gap_messages:
            lines.append(f"- {m}")
        lines.append("")
    if audit.anti_pattern_summaries:
        lines.append(f"{r.md_anti_patterns}\n")
        for a in audit.anti_pattern_summaries:
            lines.append(f"- {a}")
        lines.append("")


def _md_architecture_and_stats(lines: list[str], payload: PremiumReportPayload, r: PremiumRenderCopy) -> None:
    if payload.level == ReportLevel.EXECUTIVE:
        return
    lines.append(f"{r.md_arch_overview}\n")
    ar = payload.architecture
    lines.append(md_block(ar.narrative) + "\n")
    lines.append(f"{r.md_main_components}\n")
    lines.append("\n".join(f"- {md_block(c)}" for c in ar.main_components[:15]))
    lines.append(f"\n{r.md_main_flows}\n")
    lines.append("\n".join(f"- {md_block(f)}" for f in ar.main_flows[:15]))
    lines.append(f"\n{r.md_meth_used_vs_rec}\n")
    lines.append(f"- {r.md_used} {ar.methodology_used}")
    lines.append(f"- {r.md_recommended} {ar.methodology_recommended or r.nd}")
    if ar.recommendation_reason:
        lines.append(f"- {r.md_reason} {ar.recommendation_reason}")
    lines.append("")

    lines.append(f"{r.md_stats_distribution}\n")
    d = payload.distributions
    lines.append(
        _md_table([r.hdr_metric, r.hdr_value], [[r.md_total_threats_metric, str(d.total_threats)]], r.md_no_data)
    )
    lines.append(f"{r.md_by_stride}\n")
    lines.append(_md_table([r.hdr_stride, r.hdr_n], [[k, str(v)] for k, v in d.by_stride.items()], r.md_no_data))
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


def _md_top_risks(lines: list[str], payload: PremiumReportPayload, r: PremiumRenderCopy) -> None:
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


def _md_deep_details(lines: list[str], payload: PremiumReportPayload, r: PremiumRenderCopy) -> None:
    if payload.level == ReportLevel.EXECUTIVE:
        return
    lines.append(f"{r.md_root_cause_groups}\n")
    for rc_group in payload.root_cause_groups[:15]:
        lines.append(f"### {rc_group.display_name} (`{rc_group.key}`)\n")
        lines.append(f"- {r.md_occurrences_backlog} {rc_group.threat_count}")
        lines.append(f"- {r.md_single_fix} {rc_group.single_fix_recommendation[:400]}")
        lines.append(f"- {r.md_controls} {', '.join(rc_group.suggested_controls)}\n")

    lines.append(f"{r.md_exploit_sample}\n")
    for exp_prof in payload.exploitability_profiles[:10]:
        lines.append(f"### {exp_prof.threat_id}\n")
        lines.append(f"- {exp_prof.notes}")
        lines.append(
            f"- {r.md_locality} {exp_prof.attack_locality} · {r.md_external} {exp_prof.requires_external_access} · "
            f"{r.md_mitm} {exp_prof.requires_mitm}\n"
        )

    lines.append(f"{r.md_business_impact_labels}\n")
    for biz_row in payload.business_impacts[:10]:
        lines.append(f"- **{biz_row.threat_id}:** {', '.join(biz_row.labels)} — _{biz_row.rationale}_\n")

    lines.append(f"{r.md_quick_wins}\n")
    for qw in payload.quick_wins:
        lines.append(f"- **{qw.title}** (`{qw.backlog_item_id}`): {qw.rationale[:300]}\n")

    lines.append(f"{r.md_ownership}\n")
    for ow in payload.ownership:
        role = ow.suggested_owner_role or r.md_to_define
        lines.append(f"- **{role}:** {len(ow.backlog_item_ids)} {r.md_items} {r.md_em_dash} {ow.explanation}\n")

    lines.append(f"{r.md_strategic}\n")
    for s in payload.strategic_recommendations:
        lines.append(f"### {s.title}\n{md_block(s.detail)}\n")


def _md_roadmap(lines: list[str], payload: PremiumReportPayload, r: PremiumRenderCopy) -> None:
    lines.append(f"{r.md_roadmap}\n")
    for ph in payload.roadmap:
        lines.append(f"### {ph.title}\n")
        for it in ph.items:
            lines.append(f"- {it}")
        lines.append("")


def _md_baseline_semantic(lines: list[str], bd: object, r: PremiumRenderCopy) -> None:
    if not (
        bd.semantic_insights_from_analysis  # type: ignore[attr-defined]
        or bd.semantic_improved  # type: ignore[attr-defined]
        or bd.semantic_worsened  # type: ignore[attr-defined]
        or bd.semantic_risk_impact  # type: ignore[attr-defined]
    ):
        return
    lines.append(f"\n{r.md_semantic_diff}\n")
    lines.append(f"{r.md_semantic_diff_note}\n")
    for x in bd.semantic_insights_from_analysis[:10]:  # type: ignore[attr-defined]
        lines.append(f"- {x}")
    if bd.semantic_improved:  # type: ignore[attr-defined]
        lines.append(f"\n{r.md_improved}")
        for x in bd.semantic_improved[:8]:  # type: ignore[attr-defined]
            lines.append(f"- {x}")
    if bd.semantic_worsened:  # type: ignore[attr-defined]
        lines.append(f"\n{r.md_attention}")
        for x in bd.semantic_worsened[:8]:  # type: ignore[attr-defined]
            lines.append(f"- {x}")
    if bd.semantic_risk_impact:  # type: ignore[attr-defined]
        lines.append(f"\n{r.md_risk_impact_reading}")
        for x in bd.semantic_risk_impact[:6]:  # type: ignore[attr-defined]
            lines.append(f"- {x}")
    lines.append("")


def _md_baseline_diff(lines: list[str], payload: PremiumReportPayload, r: PremiumRenderCopy) -> None:
    if not (payload.baseline_diff and payload.baseline_diff.has_baseline):
        return
    lines.append(f"{r.md_baseline_diff}\n")
    lines.append(md_block(payload.baseline_diff.narrative) + "\n")
    lines.append(f"{r.md_new} {', '.join(payload.baseline_diff.threats_added[:20])}\n")
    lines.append(f"{r.md_removed} {', '.join(payload.baseline_diff.threats_removed[:20])}\n")
    _md_baseline_semantic(lines, payload.baseline_diff, r)


def _md_technical_appendix(lines: list[str], appendix: TechnicalAppendix, r: PremiumRenderCopy) -> None:
    """Apêndice do nível `deep`, com a sua própria cobertura declarada.

    A listagem era cortada aqui a 20 000 caracteres, a meio da palavra da última entrada e logo
    seguida de `</details>` — indistinguível de um ficheiro truncado — sobre uma listagem que o
    builder já tinha cortado. Passa a haver um único corte (o do builder, por entrada inteira) e
    uma linha que diz quantas ameaças estão à vista de quantas existem, com o caminho para as
    restantes quando ficaram de fora.
    """
    lines.append(f"{r.md_technical_appendix}\n")
    lines.append(md_block(appendix.methodology_outputs_note) + "\n")
    if appendix.import_evidence_note:
        lines.append(md_block(appendix.import_evidence_note) + "\n")
    shown = count_appendix_entries(appendix.full_threat_listing)
    coverage = r.md_appendix_coverage.format(shown=shown, total=appendix.total_threat_count)
    if shown < appendix.total_threat_count:
        coverage = f"{coverage} {r.md_appendix_truncated}"
    lines.append(f"{coverage}\n")
    lines.append(f"{r.md_threats_excerpt}\n\n")
    lines.append(appendix.full_threat_listing)
    lines.append("\n</details>\n")


def _md_tail_sections(lines: list[str], payload: PremiumReportPayload, r: PremiumRenderCopy) -> None:
    lvl = payload.level
    if lvl != ReportLevel.EXECUTIVE and payload.deduplication:
        lines.append(f"{r.md_dedup}\n")
        for dg in payload.deduplication[:10]:
            lines.append(
                f"- **{dg.group_key}** ({dg.occurrence_count}x): {dg.unified_remediation[:200]} "
                f"{r.md_dedup_ids} {', '.join(dg.threat_ids[:8])}\n"
            )

    if lvl != ReportLevel.EXECUTIVE:
        lines.append(f"{r.md_explainability}\n")
        for ex_snippet in payload.explainability[:20]:
            lines.append(f"- **[{ex_snippet.category}]** {ex_snippet.message[:400]}\n")

    if lvl == ReportLevel.DEEP and payload.technical_appendix:
        _md_technical_appendix(lines, payload.technical_appendix, r)

    if payload.methodology_voice:
        lines.append(f"{r.md_methodology_adaptation}\n")
        for v in payload.methodology_voice:
            lines.append(f"- {v}")
        lines.append("")


def render_premium_markdown(payload: PremiumReportPayload) -> str:
    """Gera Markdown completo; profundidade controlada por `payload.level`."""
    payload = _inlined(payload)
    r = premium_render_copy(payload.locale)
    lines: list[str] = []
    _md_cover_and_disclaimer(lines, payload, r)
    _md_executive_summary(lines, payload, r)
    _md_guided_audit(lines, payload, r)
    _md_architecture_and_stats(lines, payload, r)
    _md_top_risks(lines, payload, r)
    _md_deep_details(lines, payload, r)
    _md_roadmap(lines, payload, r)
    _md_baseline_diff(lines, payload, r)
    _md_tail_sections(lines, payload, r)
    lines.append(f"---\n{r.md_footer}\n")
    return "\n".join(lines)
