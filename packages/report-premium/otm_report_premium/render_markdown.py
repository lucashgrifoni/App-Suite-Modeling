"""Renderização Markdown do payload premium — um único caminho para CLI/API."""

from __future__ import annotations

from .enums import ReportLevel
from .models import PremiumReportPayload


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_Sem dados._\n"
    h = "| " + " | ".join(headers) + " |\n"
    sep = "| " + " | ".join("---" for _ in headers) + " |\n"
    body = "".join("| " + " | ".join(r) + " |\n" for r in rows)
    return h + sep + body


def render_premium_markdown(payload: PremiumReportPayload) -> str:
    """Gera Markdown completo; profundidade controlada por `payload.level`."""
    lvl = payload.level
    lines: list[str] = []

    lines.append(f"# {payload.cover.title}\n")
    lines.append("## Capa executiva\n")
    ver = payload.cover.document_version or "n/d"
    lines.append(f"- **Schema / versão documento:** {payload.cover.schema_version} / {ver}")
    lines.append(f"- **Metodologia principal:** {payload.cover.primary_methodology}")
    lines.append(f"- **Tipo de sistema / setor:** {payload.cover.system_type} · {payload.cover.industry_sector}")
    lines.append(f"- **Data da análise:** {payload.cover.analysis_date_iso}")
    lines.append(f"- **Versão App Suite Modeling:** {payload.cover.app_suite_version}")
    lines.append(f"- **Classificação de risco (heurística):** {payload.cover.overall_risk_label}")
    lines.append(f"- **Estado geral:** {payload.cover.overall_status_display}\n")

    lines.append("### Aviso de inferência\n")
    lines.append(payload.disclaimer.summary)
    for b in payload.disclaimer.bullets:
        lines.append(f"- {b}")
    lines.append("")

    lines.append("## Executive summary\n")
    es = payload.executive_summary
    lines.append(f"- **Total de ameaças (canónicas + heurísticas activas):** {es.threat_count}")
    lines.append(f"- **Urgência:** {es.urgency_level}")
    lines.append(f"- **Conclusão executiva:** {es.executive_conclusion}\n")
    lines.append("### Distribuição por severidade\n")
    lines.append(_md_table(["Severidade", "Contagem"], [[k, str(v)] for k, v in es.severity_distribution.items()]))
    lines.append("### Distribuição por metodologia (motor)\n")
    lines.append(_md_table(["Metodologia", "Ameaças"], [[k, str(v)] for k, v in es.methodology_distribution.items()]))
    lines.append("### Principais trust boundaries\n")
    lines.append("\n".join(f"- {x}" for x in es.top_trust_boundaries) or "_Nenhuma listada._")
    lines.append("\n### Principais superfícies (componentes)\n")
    lines.append("\n".join(f"- {x}" for x in es.top_attack_surfaces) or "_Nenhuma listada._")
    lines.append("\n### Top 5 riscos (título)\n")
    for t in es.top5_risk_titles:
        lines.append(f"- {t}")
    lines.append("\n### Perguntas de readiness\n")
    for q in es.readiness_questions:
        lines.append(f"- {q}")
    lines.append("")

    if payload.guided_modeling_audit:
        g = payload.guided_modeling_audit
        lines.append("## Contexto de decisão (assistente / completude)\n")
        if g.model_quality_summary_line:
            lines.append(f"- **Qualidade do modelo:** {g.model_quality_summary_line}\n")
        if g.methodology_completeness_line:
            lines.append(f"- **Metodologia:** {g.methodology_completeness_line}\n")
        if g.wizard_context_notes:
            lines.append("### Notas do assistente\n")
            for n in g.wizard_context_notes:
                lines.append(f"- {n}")
            lines.append("")
        if g.wizard_signal_trace_lines:
            lines.append("### Audit trail do assistente (resumo)\n")
            for t in g.wizard_signal_trace_lines:
                lines.append(f"- {t}")
            lines.append("")
        if g.top_model_gap_messages:
            lines.append("### Lacunas do pré-check\n")
            for m in g.top_model_gap_messages:
                lines.append(f"- {m}")
            lines.append("")
        if g.anti_pattern_summaries:
            lines.append("### Anti-padrões\n")
            for a in g.anti_pattern_summaries:
                lines.append(f"- {a}")
            lines.append("")

    if lvl != ReportLevel.EXECUTIVE:
        lines.append("## Visão arquitetural resumida\n")
        ar = payload.architecture
        lines.append(ar.narrative + "\n")
        lines.append("### Componentes principais\n")
        lines.append("\n".join(f"- {c}" for c in ar.main_components[:15]))
        lines.append("\n### Fluxos principais\n")
        lines.append("\n".join(f"- {f}" for f in ar.main_flows[:15]))
        lines.append("\n### Metodologia usada vs recomendada\n")
        lines.append(f"- **Usada:** {ar.methodology_used}")
        lines.append(f"- **Recomendada:** {ar.methodology_recommended or 'n/d'}")
        if ar.recommendation_reason:
            lines.append(f"- **Motivo:** {ar.recommendation_reason}")
        lines.append("")

    if lvl != ReportLevel.EXECUTIVE:
        lines.append("## Estatísticas e distribuição\n")
        d = payload.distributions
        lines.append(_md_table(["Métrica", "Valor"], [["Total de ameaças", str(d.total_threats)]]))
        lines.append("### Por STRIDE\n")
        lines.append(_md_table(["STRIDE", "N"], [[k, str(v)] for k, v in d.by_stride.items()]))
        lines.append("### Heatmap STRIDE × severidade (contagens)\n")
        for sk, row in d.heatmap_stride_severity.items():
            lines.append(f"**{sk}:** " + ", ".join(f"{bk}={bv}" for bk, bv in row.items()))
        lines.append("\n### Ranking de componentes (score agregado heurístico)\n")
        lines.append(
            _md_table(
                ["Componente", "Score"],
                [[str(a), f"{b:.3f}"] for a, b in d.top_components_ranked[:10]],
            )
        )
        lines.append("")

    lines.append("## Top 10 riscos prioritários\n")
    lines.append(
        _md_table(
            ["#", "ID", "Título", "P", "Tier", "Acção resumida"],
            [
                [
                    str(r.rank),
                    r.threat_id,
                    r.title[:80],
                    f"{r.composite_score:.2f}",
                    r.priority_tier,
                    r.recommended_action[:120].replace("|", "/"),
                ]
                for r in payload.top_risks
            ],
        )
    )
    lines.append("")

    if lvl != ReportLevel.EXECUTIVE:
        lines.append("## Agrupamento por causa raiz\n")
        for g in payload.root_cause_groups[:15]:
            lines.append(f"### {g.display_name} (`{g.key}`)\n")
            lines.append(f"- **Ocorrências (itens de backlog):** {g.threat_count}")
            lines.append(f"- **Correção única sugerida:** {g.single_fix_recommendation[:400]}")
            lines.append(f"- **Controlos:** {', '.join(g.suggested_controls)}\n")

        lines.append("## Contexto de exploração (amostra)\n")
        for ex in payload.exploitability_profiles[:10]:
            lines.append(f"### {ex.threat_id}\n")
            lines.append(f"- {ex.notes}")
            lines.append(
                f"- Localidade: {ex.attack_locality} · externo: {ex.requires_external_access} · "
                f"MITM: {ex.requires_mitm}\n"
            )

        lines.append("## Impacto de negócio (etiquetas sugeridas)\n")
        for b in payload.business_impacts[:10]:
            lines.append(f"- **{b.threat_id}:** {', '.join(b.labels)} — _{b.rationale}_\n")

    if lvl != ReportLevel.EXECUTIVE:
        lines.append("## Quick wins\n")
        for qw in payload.quick_wins:
            lines.append(f"- **{qw.title}** (`{qw.backlog_item_id}`): {qw.rationale[:300]}\n")

        lines.append("## Ownership sugerido (papel lógico)\n")
        for ow in payload.ownership:
            role = ow.suggested_owner_role or "a definir"
            lines.append(f"- **{role}:** {len(ow.backlog_item_ids)} itens — {ow.explanation}\n")

        lines.append("## Recomendações estratégicas\n")
        for s in payload.strategic_recommendations:
            lines.append(f"### {s.title}\n{s.detail}\n")

    lines.append("## Roadmap de remediação\n")
    for ph in payload.roadmap:
        lines.append(f"### {ph.title}\n")
        for it in ph.items:
            lines.append(f"- {it}")
        lines.append("")

    if payload.baseline_diff and payload.baseline_diff.has_baseline:
        lines.append("## Baseline / diff\n")
        lines.append(payload.baseline_diff.narrative + "\n")
        lines.append(f"- Novos: {', '.join(payload.baseline_diff.threats_added[:20])}\n")
        lines.append(f"- Removidos: {', '.join(payload.baseline_diff.threats_removed[:20])}\n")
        bd = payload.baseline_diff
        if (
            bd.semantic_insights_from_analysis
            or bd.semantic_improved
            or bd.semantic_worsened
            or bd.semantic_risk_impact
        ):
            lines.append("\n### Diff semântico (entre execuções de análise)\n")
            lines.append(
                "_Heurística sobre pré-check, anti-patterns e ranking — não atribui causa a alterações no YAML._\n"
            )
            for x in bd.semantic_insights_from_analysis[:10]:
                lines.append(f"- {x}")
            if bd.semantic_improved:
                lines.append("\n_Melhorou:_")
                for x in bd.semantic_improved[:8]:
                    lines.append(f"- {x}")
            if bd.semantic_worsened:
                lines.append("\n_Atenção:_")
                for x in bd.semantic_worsened[:8]:
                    lines.append(f"- {x}")
            if bd.semantic_risk_impact:
                lines.append("\n_Impacto de risco (leitura):_")
                for x in bd.semantic_risk_impact[:6]:
                    lines.append(f"- {x}")
            lines.append("")

    if lvl != ReportLevel.EXECUTIVE and payload.deduplication:
        lines.append("## Deduplicação inteligente\n")
        for dg in payload.deduplication[:10]:
            lines.append(
                f"- **{dg.group_key}** ({dg.occurrence_count}x): {dg.unified_remediation[:200]} "
                f"— IDs: {', '.join(dg.threat_ids[:8])}\n"
            )

    if lvl != ReportLevel.EXECUTIVE:
        lines.append("## Explainability\n")
        for ex in payload.explainability[:20]:
            lines.append(f"- **[{ex.category}]** {ex.message[:400]}\n")

    if lvl == ReportLevel.DEEP and payload.technical_appendix:
        lines.append("## Apêndice técnico\n")
        lines.append(payload.technical_appendix.methodology_outputs_note + "\n")
        if payload.technical_appendix.import_evidence_note:
            lines.append(payload.technical_appendix.import_evidence_note + "\n")
        lines.append("<details><summary>Ameaças (trecho)</summary>\n\n")
        lines.append(payload.technical_appendix.full_threat_listing[:20000])
        lines.append("\n</details>\n")

    if payload.methodology_voice:
        lines.append("## Adaptação por metodologia\n")
        for v in payload.methodology_voice:
            lines.append(f"- {v}")
        lines.append("")

    lines.append("---\n*Gerado pelo App Suite Modeling — report premium.*\n")
    return "\n".join(lines)
