"""Relatório Markdown para `ThreatModelComparisonResult` (diff estrutural + análise)."""

from __future__ import annotations

from otm_threat_engine.comparison_models import ThreatModelComparisonResult


def export_comparison_markdown(result: ThreatModelComparisonResult) -> str:
    """Gera relatório legível: resumo, insights, deltas e próximos passos."""
    lines: list[str] = [
        "## Diff de threat model",
        "",
        "### Resumo executivo",
        "",
        f"- {result.summary.headline}",
        f"- Mudanças estruturais: {'sim' if result.summary.has_structural_changes else 'não'}",
        f"- Mudanças na análise: {'sim' if result.summary.has_analysis_changes else 'não'}",
        f"- Metodologia no documento alterada: {'sim' if result.summary.methodology_in_model_changed else 'não'}",
        "",
        "### Principais insights",
        "",
    ]
    for i, ins in enumerate(result.key_insights[:20], 1):
        lines.append(f"{i}. {ins}")
    if not result.key_insights:
        lines.append("_Nenhum insight automático._")
    if result.explanations:
        lines.extend(["", "### Explicabilidade (foco)", ""])
        for ex in result.explanations[:6]:
            lines.append(f"- **{ex.subject}** — {ex.message}")
        lines.append("")
    lines.extend(["", "### Agregado estrutural (IDs)", ""])

    for name in ("components", "assets", "data_flows", "trust_boundaries", "threats", "mitigations", "evidence_suggestions"):
        block = getattr(result.aggregate, name)
        if not any(block.get(k) for k in ("added", "removed", "changed")):
            continue
        lines.append(f"- **{name}**: +{len(block['added'])} / −{len(block['removed'])} / ~{len(block['changed'])}")
    lines.extend(["", "### Delta de risco (análise)", ""])
    rd = result.risk_delta
    lines.append(
        f"- Score máximo heurístico: {rd.analysis_max_score_baseline} → {rd.analysis_max_score_revised} "
        f"(Δ {rd.analysis_max_score_delta!s})"
    )
    lines.append(f"- Residual no documento (YAML) alterado: {'sim' if rd.document_residual_aggregate_changed else 'não'}")
    if rd.heuristic_increased_ids:
        lines.append(f"- Heurísticas com maior exposição ou novas: `{', '.join(rd.heuristic_increased_ids[:15])}`")
    if rd.heuristic_decreased_ids:
        lines.append(f"- Heurísticas removidas ou com score a baixar: `{', '.join(rd.heuristic_decreased_ids[:15])}`")

    lines.extend(["", "### Recomendações e cobertura", ""])
    rec = result.recommendation_delta
    if rec.pack_hints_added:
        lines.append(f"- Novos controlos (pack): {'; '.join(rec.pack_hints_added[:8])}")
    if rec.pack_hints_removed:
        lines.append(f"- Controlos pack deixaram de surgir: {'; '.join(rec.pack_hints_removed[:8])}")
    for fr in rec.framework_catalog_deltas[:6]:
        lines.append(f"- Framework `{fr.catalog}`: {fr.count_before} → {fr.count_after}")

    lines.extend(["", "### Próximos passos sugeridos", ""])
    lines.extend(
        [
            "1. Rever em workshop os itens em «Principais insights» com AppSec e equipa.",
            "2. Atualizar backlog: ameaças canónicas e heurísticas novas ou com Δ de score.",
            "3. Reexecutar análise após mudança de metodologia no modelo ou no motor.",
            "4. Para revisão de PR, anexar este relatório ou o JSON completo (`ThreatModelComparisonResult`).",
            "",
        ]
    )
    return "\n".join(lines)
