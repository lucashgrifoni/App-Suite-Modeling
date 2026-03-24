"""Relatório Markdown legível a partir do documento canónico (sem CLI)."""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument


def export_document_markdown(doc: ThreatModelDocument) -> str:
    """Componentes, fluxos, fronteiras, ameaças e mitigações em Markdown simples."""
    m = doc.metadata
    lines: list[str] = [
        f"# {m.title}",
        "",
    ]
    if m.summary:
        lines.append(m.summary)
        lines.append("")
    if m.owner:
        lines.append(f"**Responsável:** {m.owner}")
    if m.document_version:
        lines.append(f"**Versão do documento:** {m.document_version}")
    lines.append("")
    lines.append(f"- **Schema:** {doc.model_info.schema_version}")
    lines.append(f"- **Tipo de sistema:** {doc.model_info.system_type.value}")
    lines.append(f"- **Setor:** {doc.model_info.industry_sector.value}")
    lines.append("")

    if doc.business_context and doc.business_context.description:
        lines.append("## Contexto de negócio")
        lines.append("")
        lines.append(doc.business_context.description.strip())
        lines.append("")

    if doc.assets:
        lines.append("## Ativos")
        lines.append("")
        for a in doc.assets:
            lines.append(f"- **{a.name}** (`{a.id}`) — {a.asset_kind.value}")
        lines.append("")

    if doc.components:
        lines.append("## Componentes")
        lines.append("")
        for c in doc.components:
            tb = f", fronteira `{c.in_trust_boundary}`" if c.in_trust_boundary else ""
            tech = f" — {c.technology}" if c.technology else ""
            lines.append(f"- **{c.name}** (`{c.id}`) — {c.kind.value}{tech}{tb}")
        lines.append("")

    if doc.data_flows:
        lines.append("## Fluxos de dados")
        lines.append("")
        for f in doc.data_flows:
            nm = f.name or f.id
            lines.append(
                f"- **{nm}** (`{f.id}`): `{f.from_component}` → `{f.to_component}`"
            )
        lines.append("")

    if doc.trust_boundaries:
        lines.append("## Fronteiras de confiança")
        lines.append("")
        for b in doc.trust_boundaries:
            lines.append(f"- **{b.name}** (`{b.id}`)")
        lines.append("")

    if doc.threats:
        lines.append("## Ameaças")
        lines.append("")
        for t in doc.threats:
            risk = ""
            if t.risk:
                risk = f" — risco L×I={t.risk.likelihood}×{t.risk.impact}"
                if t.risk.score is not None:
                    risk += f" (score {t.risk.score})"
            lines.append(f"- **{t.title}** (`{t.id}`) [{t.stride.value}]{risk}")
        lines.append("")

    if doc.mitigations:
        lines.append("## Mitigações")
        lines.append("")
        for m in doc.mitigations:
            lines.append(f"- **{m.title}** (`{m.id}`) — {m.status.value}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"
