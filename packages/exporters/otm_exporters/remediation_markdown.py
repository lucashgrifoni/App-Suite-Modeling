"""Report Markdown para backlog de remediação."""

from __future__ import annotations

from otm_threat_engine.remediation import BacklogItem, RemediationBacklog

from otm_exporters.markdown_text import md_inline


def _append_item_details(lines: list[str], id_to_item: dict[str, BacklogItem], title: str, ids: list[str]) -> None:
    lines.extend([f"## {title}", ""])
    if not ids:
        lines.append("_Nenhum._")
        lines.append("")
        return
    for iid in ids[:25]:
        it = id_to_item.get(iid)
        if not it:
            continue  # pragma: no cover - defensive: skip empty item
        lines.append(f"### {it.id}: {md_inline(it.title)}")
        lines.append("")
        lines.append(
            f"- **Prioridade:** {md_inline(it.priority_label)} (rank {it.priority_rank}) — "
            f"{md_inline(it.priority_explanation)}"
        )
        lines.append(f"- **Esforço:** {md_inline(it.effort_estimate)} · **Impacto:** {md_inline(it.impact_estimate)}")
        if it.recommended_owner:
            lines.append(
                f"- **Owner sugerido:** `{md_inline(it.recommended_owner)}` — {md_inline(it.owner_explanation)}"
            )
        else:
            lines.append(f"- **Owner:** _a definir_ — {md_inline(it.owner_explanation)}")
        if it.quick_win:
            lines.append(f"- **Quick win:** sim — {md_inline(it.quick_win_explanation)}")
        if it.foundational:
            lines.append(f"- **Foundational:** sim — {md_inline(it.foundational_explanation)}")
        if it.depends_on_action_ids:
            lines.append(f"- **Depende de:** {', '.join(it.depends_on_action_ids)}")
        lines.append(f"- **Próximo passo:** {md_inline(it.next_step)}")
        lines.append("")
        lines.append("**Porquê (explainability):**")
        for ex in it.explainability:
            lines.append(f"- {md_inline(ex)}")
        lines.append("")


def _append_high_impact_high_effort(
    lines: list[str], backlog: RemediationBacklog, id_to_item: dict[str, BacklogItem]
) -> None:
    lines.extend(["## Alto impacto / alto esforço", ""])
    lines.append("### Maior impacto estimado")
    for iid in backlog.high_impact_ids[:15]:
        it = id_to_item.get(iid)
        if it:
            lines.append(f"- `{it.id}` — {md_inline(it.title)}")
    lines.append("")
    lines.append("### Maior esforço estimado")
    for iid in backlog.high_effort_ids[:15]:
        it = id_to_item.get(iid)
        if it:
            lines.append(f"- `{it.id}` — {md_inline(it.title)}")
    lines.append("")


def _append_groupings(
    lines: list[str], backlog: RemediationBacklog, id_to_item: dict[str, BacklogItem], group_by: str | None
) -> None:
    lines.extend(["## Agrupamentos", ""])
    if group_by == "control":
        mapping = backlog.by_control_type
        label = "controlo sugerido"
    elif group_by == "category":
        mapping = backlog.by_control_category
        label = "categoria"
    else:
        mapping = backlog.by_root_cause
        label = "causa raiz"

    lines.append(f"_Agrupado por: **{label}**._")
    lines.append("")
    for key in sorted(mapping.keys()):
        ids = mapping[key]
        lines.append(f"### `{md_inline(key)}` ({len(ids)} itens)")
        for iid in ids[:12]:
            it = id_to_item.get(iid)
            if it:
                lines.append(f"- {it.id}: {md_inline(it.title)}")
        if len(ids) > 12:
            lines.append(f"- _… +{len(ids) - 12} itens_")
        lines.append("")


def export_remediation_backlog_markdown(
    backlog: RemediationBacklog,
    *,
    group_by: str | None = None,
) -> str:
    """
    Gera relatório legível.

    `group_by`: `root-cause` | `control` | `category` — reordena secção "Agrupamentos";
    o conteúdo dos itens não muda.
    """
    lines: list[str] = [
        "# Backlog de remediação (sugerido)",
        "",
        f"**Documento:** {md_inline(backlog.document_title)} · **Metodologia:** {md_inline(backlog.methodology)} · "
        f"**Contrato** `{backlog.schema_version}`",
        "",
        "## Resumo executivo",
        "",
        md_inline(backlog.executive_summary),
        "",
    ]
    if backlog.synergy_notes:
        lines.extend(["### Notas transversais", ""])
        for n in backlog.synergy_notes:
            lines.append(f"- {md_inline(n)}")
        lines.append("")

    id_to_item = {i.id: i for i in backlog.items}
    _append_item_details(lines, id_to_item, "Top 5 ações", backlog.top_5_action_ids)
    _append_item_details(lines, id_to_item, "Quick wins", backlog.quick_win_ids)
    _append_item_details(lines, id_to_item, "Ações foundational", backlog.foundational_ids)
    _append_high_impact_high_effort(lines, backlog, id_to_item)
    _append_groupings(lines, backlog, id_to_item, group_by)

    lines.extend(["## Todos os itens (ordem de prioridade)", ""])
    for it in sorted(backlog.items, key=lambda x: x.priority_rank):
        lines.append(
            f"{it.priority_rank}. **{it.id}** — {md_inline(it.title)} "
            f"({md_inline(it.priority_label)}, esforço {md_inline(it.effort_estimate)})"
        )
    lines.append("")
    lines.append(
        "---\n*Gerado automaticamente — revisar antes de comprometer roadmap; não substitui gestão de projecto.*"
    )
    return "\n".join(lines)
