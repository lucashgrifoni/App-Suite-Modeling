"""Report Markdown para backlog de remediação."""

from __future__ import annotations

from otm_threat_engine.remediation import RemediationBacklog


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
        f"**Documento:** {backlog.document_title} · **Metodologia:** {backlog.methodology} · "
        f"**Contrato** `{backlog.schema_version}`",
        "",
        "## Resumo executivo",
        "",
        backlog.executive_summary,
        "",
    ]
    if backlog.synergy_notes:
        lines.extend(["### Notas transversais", ""])
        for n in backlog.synergy_notes:
            lines.append(f"- {n}")
        lines.append("")

    id_to_item = {i.id: i for i in backlog.items}

    def append_item_details(title: str, ids: list[str]) -> None:
        lines.extend([f"## {title}", ""])
        if not ids:
            lines.append("_Nenhum._")
            lines.append("")
            return
        for iid in ids[:25]:
            it = id_to_item.get(iid)
            if not it:
                continue
            lines.append(f"### {it.id}: {it.title}")
            lines.append("")
            lines.append(f"- **Prioridade:** {it.priority_label} (rank {it.priority_rank}) — {it.priority_explanation}")
            lines.append(f"- **Esforço:** {it.effort_estimate} · **Impacto:** {it.impact_estimate}")
            if it.recommended_owner:
                lines.append(f"- **Owner sugerido:** `{it.recommended_owner}` — {it.owner_explanation}")
            else:
                lines.append(f"- **Owner:** _a definir_ — {it.owner_explanation}")
            if it.quick_win:
                lines.append(f"- **Quick win:** sim — {it.quick_win_explanation}")
            if it.foundational:
                lines.append(f"- **Foundational:** sim — {it.foundational_explanation}")
            if it.depends_on_action_ids:
                lines.append(f"- **Depende de:** {', '.join(it.depends_on_action_ids)}")
            lines.append(f"- **Próximo passo:** {it.next_step}")
            lines.append("")
            lines.append("**Porquê (explainability):**")
            for ex in it.explainability:
                lines.append(f"- {ex}")
            lines.append("")

    append_item_details("Top 5 ações", backlog.top_5_action_ids)
    append_item_details("Quick wins", backlog.quick_win_ids)
    append_item_details("Ações foundational", backlog.foundational_ids)

    lines.extend(["## Alto impacto / alto esforço", ""])
    lines.append("### Maior impacto estimado")
    for iid in backlog.high_impact_ids[:15]:
        it = id_to_item.get(iid)
        if it:
            lines.append(f"- `{it.id}` — {it.title}")
    lines.append("")
    lines.append("### Maior esforço estimado")
    for iid in backlog.high_effort_ids[:15]:
        it = id_to_item.get(iid)
        if it:
            lines.append(f"- `{it.id}` — {it.title}")
    lines.append("")

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
        lines.append(f"### `{key}` ({len(ids)} itens)")
        for iid in ids[:12]:
            it = id_to_item.get(iid)
            if it:
                lines.append(f"- {it.id}: {it.title}")
        if len(ids) > 12:
            lines.append(f"- _… +{len(ids) - 12} itens_")
        lines.append("")

    lines.extend(["## Todos os itens (ordem de prioridade)", ""])
    for it in sorted(backlog.items, key=lambda x: x.priority_rank):
        lines.append(
            f"{it.priority_rank}. **{it.id}** — {it.title} ({it.priority_label}, esforço {it.effort_estimate})"
        )
    lines.append("")
    lines.append(
        "---\n*Gerado automaticamente — revisar antes de comprometer roadmap; não substitui gestão de projecto.*"
    )
    return "\n".join(lines)
