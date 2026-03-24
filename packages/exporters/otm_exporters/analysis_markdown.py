"""Secção Markdown do resultado de análise (motor) — reutilizável por API e relatórios."""

from __future__ import annotations

from otm_core_schema import FrameworkRef, ThreatModelDocument
from otm_framework_mappings import framework_display_name
from otm_threat_engine import AnalysisResult


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
        "Contagem de referências `framework:control_id` nas heurísticas "
        "(por catálogo canónico):"
    )
    lines.append("")
    for fw, n in sorted(s.framework_ref_counts_by_catalog.items()):
        label = framework_display_name(fw)
        lines.append(f"- **{label}** (`{fw}`): {n}")
    lines.append("")


def _append_heuristic_block(
    lines: list[str],
    result: AnalysisResult,
    *,
    max_heuristic_rows: int,
) -> None:
    active = [h for h in result.heuristic_threats if not h.skipped_as_duplicate]
    if not active:
        return
    lines.append("### Ameaças sugeridas (heurística)")
    lines.append("")
    lines.append(
        "Cada entrada inclui referências de controlo (OWASP TM/ASVS, NIST CSF, ISO 27001) "
        "derivadas do STRIDE."
    )
    lines.append("")
    for h in active[:max_heuristic_rows]:
        tgt = h.target_component_id or h.target_data_flow_id or "—"
        sc = h.risk.score if h.risk.score is not None else "—"
        refs = _format_framework_refs_compact(h.framework_refs)
        lines.append(
            f"- **{h.title}** (`{h.id}`) → alvo `{tgt}` — score {sc}  \n"
            f"  - Frameworks: {refs}"
        )
    if len(active) > max_heuristic_rows:
        lines.append(f"\n… e mais {len(active) - max_heuristic_rows} entradas.")
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


def _append_executive_summary(lines: list[str], result: AnalysisResult) -> None:
    s = result.summary
    active = [h for h in result.heuristic_threats if not h.skipped_as_duplicate]
    top = sorted(active, key=lambda h: h.risk.score or 0.0, reverse=True)[:3]
    lines.append("### Resumo executivo")
    lines.append("")
    lines.append(
        f"- Total de ameaças ativas: **{len(active)}** · Maior score: **{s.max_risk_score if s.max_risk_score is not None else '—'}**"
    )
    lines.append(f"- Metodologia aplicada: **{result.methodology.value}**")
    if top:
        lines.append("- Prioridade imediata:")
        for h in top:
            tgt = h.target_component_id or h.target_data_flow_id or "escopo geral"
            lines.append(f"  - {h.title} (score {h.risk.score}) em `{tgt}`")
    lines.append("")


def _append_next_steps(lines: list[str], result: AnalysisResult) -> None:
    active = [h for h in result.heuristic_threats if not h.skipped_as_duplicate]
    top = sorted(active, key=lambda h: h.risk.score or 0.0, reverse=True)[:5]
    lines.append("### Próximos passos sugeridos")
    lines.append("")
    if not top:
        lines.append("- Sem ameaças ativas de alta prioridade nesta execução.")
        lines.append("")
        return
    lines.append("- Validar os 3 maiores riscos em workshop curto com engenharia e segurança.")
    lines.append("- Converter os achados críticos em backlog com owner e prazo.")
    lines.append("- Revisar controles de acesso, integridade de fluxo e proteção de dados sensíveis.")
    if result.methodology_insights and result.methodology_insights.profile:
        lines.append(
            f"- Usar os insights do perfil **{result.methodology_insights.profile}** para priorização contextual."
        )
    lines.append("")


def export_analysis_markdown(result: AnalysisResult, *, max_heuristic_rows: int = 50) -> str:
    """
    Relatório da análise heurística: totais, frameworks, achados e ameaças sugeridas.
    Não inclui o documento canónico — use `export_document_and_analysis_markdown` para o pacote completo.
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
    _append_executive_summary(lines, result)
    _append_methodology_insights_block(lines, result)
    _append_heuristic_block(lines, result, max_heuristic_rows=max_heuristic_rows)
    _append_next_steps(lines, result)
    return "\n".join(lines)


def export_document_and_analysis_markdown(
    doc: ThreatModelDocument,
    result: AnalysisResult,
) -> str:
    """Concatena Markdown do documento e da análise (atalho para relatórios)."""
    from otm_exporters.document_markdown import export_document_markdown

    return export_document_markdown(doc) + "\n" + export_analysis_markdown(result)
