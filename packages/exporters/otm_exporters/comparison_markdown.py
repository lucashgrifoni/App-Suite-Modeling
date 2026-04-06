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
    meta = result.meta
    disc = meta.interpretation_disclaimer
    if isinstance(disc, str) and disc.strip():
        lines.extend(["", "### Aviso inferencial (diff)", "", f"_{disc}_", ""])

    sem = meta.semantic_diff_sections
    if sem is not None:
        improved = sem.improved or []
        worsened = sem.worsened or []
        risk_impact = sem.risk_impact or []
        scs = sem.structural_change_summary or []
        if improved or worsened or risk_impact or scs:
            lines.extend(["", "### Diff semântico (resumo)", ""])
            lines.append(
                "_Agregado heurístico (estrutura + análise). Não atribui causalidade fina a campos individuais._"
            )
            lines.append("")
            if scs:
                lines.append("_Mudanças estruturais (contagens de IDs):_")
                for item in scs[:6]:
                    lines.append(f"- {item}")
                lines.append("")
            if improved:
                lines.append("_Melhorias / convergência:_")
                for item in improved[:8]:
                    lines.append(f"- {item}")
                lines.append("")
            if worsened:
                lines.append("_Atenção / regressão aparente:_")
                for item in worsened[:8]:
                    lines.append(f"- {item}")
                lines.append("")
            if risk_impact:
                lines.append("_Impacto em risco (heurístico):_")
                for item in risk_impact[:6]:
                    lines.append(f"- {item}")
                lines.append("")
    refs = meta.semantic_structural_refs
    if refs:
        lines.extend(["", "### Ligação estrutura → interpretação (refs estáveis)", ""])
        for item in refs[:20]:
            cc = f" · `{item.change_category}`" if item.change_category else ""
            lines.append(f"- `{item.ref}` · {item.entity_kind} `{item.entity_id}`{cc} — {item.note}")
        lines.append("")
    links = meta.semantic_interpretation_links
    if links:
        lines.extend(
            [
                "",
                "### Correspondência ref → interpretação (v1.5)",
                "",
                (
                    "_Cada linha inclui `anchoring_rationale`. `inference_strength=medium` só com ≥2 tokens "
                    "lexicais; tópico = `low`. Sem causalidade provada._"
                ),
                "",
            ]
        )
        for item in links[:16]:
            tok = ", ".join(item.shared_tokens) if item.shared_tokens else "—"
            rationale = (item.anchoring_rationale or "").replace("\n", " ")
            lines.append(
                f"- `{item.structural_ref}` → **{item.related_section}** "
                f"(`{item.link_kind}`, {item.inference_strength}; tokens: {tok}): {item.summary}"
            )
            if rationale:
                lines.append(f"  - _Porquê:_ {rationale}")
        lines.append("")
    si = meta.semantic_insights
    if si:
        lines.extend(["", "### Insights semânticos (narrativa)", ""])
        for item in si[:14]:
            lines.append(f"- {item}")
        lines.append("")
    if result.explanations:
        lines.extend(["", "### Explicabilidade (foco)", ""])
        for ex in result.explanations[:6]:
            lines.append(f"- **{ex.subject}** — {ex.message}")
        lines.append("")
    lines.extend(["", "### Agregado estrutural (IDs)", ""])

    _agg_names = (
        "components",
        "assets",
        "data_flows",
        "trust_boundaries",
        "threats",
        "mitigations",
        "evidence_suggestions",
    )
    for name in _agg_names:
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
    res_changed = "sim" if rd.document_residual_aggregate_changed else "não"
    lines.append(f"- Residual no documento (YAML) alterado: {res_changed}")
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
