"""Relatório Markdown para `ThreatModelComparisonResult` (diff estrutural + análise)."""

from __future__ import annotations

from otm_threat_engine.comparison_models import ThreatModelComparisonResult


def _cmp_bullets(lines: list[str], header: str, items: list[str], limit: int) -> None:
    if not items:
        return
    lines.append(header)
    for item in items[:limit]:
        lines.append(f"- {item}")
    lines.append("")


def _cmp_semantic_diff(lines: list[str], result: ThreatModelComparisonResult) -> None:
    sem = result.meta.semantic_diff_sections
    if sem is None:  # pragma: no cover - enrich_comparison_meta always sets semantic_diff_sections
        return
    improved = sem.improved or []
    worsened = sem.worsened or []
    risk_impact = sem.risk_impact or []
    scs = sem.structural_change_summary or []
    if not (improved or worsened or risk_impact or scs):  # noqa: E501  # pragma: no cover - structural_change_summary always populated
        return
    lines.extend(["", "### Diff semântico (resumo)", ""])
    lines.append(
        "_Agregado heurístico (estrutura + análise). Não atribui causalidade fina a campos individuais._"
    )
    lines.append("")
    _cmp_bullets(lines, "_Mudanças estruturais (contagens de IDs):_", scs, 6)
    _cmp_bullets(lines, "_Melhorias / convergência:_", improved, 8)
    _cmp_bullets(lines, "_Atenção / regressão aparente:_", worsened, 8)
    _cmp_bullets(lines, "_Impacto em risco (heurístico):_", risk_impact, 6)


def _cmp_structural_refs(lines: list[str], result: ThreatModelComparisonResult) -> None:
    refs = result.meta.semantic_structural_refs
    if not refs:
        return
    lines.extend(["", "### Ligação estrutura → interpretação (refs estáveis)", ""])
    for ref_row in refs[:20]:
        cc = f" · `{ref_row.change_category}`" if ref_row.change_category else ""
        lines.append(f"- `{ref_row.ref}` · {ref_row.entity_kind} `{ref_row.entity_id}`{cc} — {ref_row.note}")
    lines.append("")


def _cmp_interpretation_links(lines: list[str], result: ThreatModelComparisonResult) -> None:
    links = result.meta.semantic_interpretation_links
    if not links:
        return
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
    for link_row in links[:16]:
        tok = ", ".join(link_row.shared_tokens) if link_row.shared_tokens else "—"
        rationale = (link_row.anchoring_rationale or "").replace("\n", " ")
        lines.append(
            f"- `{link_row.structural_ref}` → **{link_row.related_section}** "
            f"(`{link_row.link_kind}`, {link_row.inference_strength}; tokens: {tok}): {link_row.summary}"
        )
        if rationale:
            lines.append(f"  - _Porquê:_ {rationale}")
    lines.append("")


def _cmp_semantic_insights(lines: list[str], result: ThreatModelComparisonResult) -> None:
    si = result.meta.semantic_insights
    if not si:
        return
    lines.extend(["", "### Insights semânticos (narrativa)", ""])
    for insight_line in si[:14]:
        lines.append(f"- {insight_line}")
    lines.append("")


def _cmp_explanations(lines: list[str], result: ThreatModelComparisonResult) -> None:
    if not result.explanations:
        return
    lines.extend(["", "### Explicabilidade (foco)", ""])
    for ex in result.explanations[:6]:
        lines.append(f"- **{ex.subject}** — {ex.message}")
    lines.append("")


def _cmp_structural_aggregate(lines: list[str], result: ThreatModelComparisonResult) -> None:
    lines.extend(["", "### Agregado estrutural (IDs)", ""])
    agg_names = (
        "components",
        "assets",
        "data_flows",
        "trust_boundaries",
        "threats",
        "mitigations",
        "evidence_suggestions",
    )
    for name in agg_names:
        block = getattr(result.aggregate, name)
        if not any(block.get(k) for k in ("added", "removed", "changed")):
            continue
        lines.append(f"- **{name}**: +{len(block['added'])} / −{len(block['removed'])} / ~{len(block['changed'])}")


def _cmp_risk_delta(lines: list[str], result: ThreatModelComparisonResult) -> None:
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


def _cmp_recommendations(lines: list[str], result: ThreatModelComparisonResult) -> None:
    lines.extend(["", "### Recomendações e cobertura", ""])
    rec = result.recommendation_delta
    if rec.pack_hints_added:
        lines.append(f"- Novos controlos (pack): {'; '.join(rec.pack_hints_added[:8])}")
    if rec.pack_hints_removed:
        lines.append(f"- Controlos pack deixaram de surgir: {'; '.join(rec.pack_hints_removed[:8])}")
    for fr in rec.framework_catalog_deltas[:6]:
        lines.append(f"- Framework `{fr.catalog}`: {fr.count_before} → {fr.count_after}")


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

    _cmp_semantic_diff(lines, result)
    _cmp_structural_refs(lines, result)
    _cmp_interpretation_links(lines, result)
    _cmp_semantic_insights(lines, result)
    _cmp_explanations(lines, result)
    _cmp_structural_aggregate(lines, result)
    _cmp_risk_delta(lines, result)
    _cmp_recommendations(lines, result)

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
