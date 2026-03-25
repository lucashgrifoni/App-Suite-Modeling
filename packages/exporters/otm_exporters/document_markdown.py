"""
Relatório Markdown legível a partir do documento canónico (sem CLI).

Ordem das secções e regressão: `tests/test_exporters.py` (procurar
`document_markdown` / `heading_order`).
"""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument


def _append_header(lines: list[str], doc: ThreatModelDocument) -> None:
    m = doc.metadata
    lines.extend([f"# {m.title}", ""])
    if m.summary:
        lines.extend([m.summary, ""])
    if m.owner:
        lines.append(f"**Responsável:** {m.owner}")
    if m.document_version:
        lines.append(f"**Versão do documento:** {m.document_version}")
    lines.extend(
        [
            "",
            f"- **Schema:** {doc.model_info.schema_version}",
            f"- **Tipo de sistema:** {doc.model_info.system_type.value}",
            f"- **Setor:** {doc.model_info.industry_sector.value}",
            "",
        ]
    )


def _append_section(lines: list[str], title: str) -> None:
    lines.extend([f"## {title}", ""])


def _append_bulleted(lines: list[str], items: list[str]) -> None:
    lines.extend(items)
    lines.append("")


def _append_business_context(lines: list[str], doc: ThreatModelDocument) -> None:
    if not (doc.business_context and doc.business_context.description):
        return
    _append_section(lines, "Contexto de negócio")
    lines.extend([doc.business_context.description.strip(), ""])


def _append_assets(lines: list[str], doc: ThreatModelDocument) -> None:
    if not doc.assets:
        return
    _append_section(lines, "Ativos")
    _append_bulleted(
        lines,
        [f"- **{a.name}** (`{a.id}`) — {a.asset_kind.value}" for a in doc.assets],
    )


def _append_components(lines: list[str], doc: ThreatModelDocument) -> None:
    if not doc.components:
        return
    _append_section(lines, "Componentes")
    items: list[str] = []
    for c in doc.components:
        tb = f", fronteira `{c.in_trust_boundary}`" if c.in_trust_boundary else ""
        tech = f" — {c.technology}" if c.technology else ""
        items.append(f"- **{c.name}** (`{c.id}`) — {c.kind.value}{tech}{tb}")
    _append_bulleted(lines, items)


def _append_data_flows(lines: list[str], doc: ThreatModelDocument) -> None:
    if not doc.data_flows:
        return
    _append_section(lines, "Fluxos de dados")
    items: list[str] = []
    for f in doc.data_flows:
        nm = f.name or f.id
        items.append(f"- **{nm}** (`{f.id}`): `{f.from_component}` → `{f.to_component}`")
    _append_bulleted(lines, items)


def _append_trust_boundaries(lines: list[str], doc: ThreatModelDocument) -> None:
    if not doc.trust_boundaries:
        return
    _append_section(lines, "Fronteiras de confiança")
    _append_bulleted(lines, [f"- **{b.name}** (`{b.id}`)" for b in doc.trust_boundaries])


def _append_threats(lines: list[str], doc: ThreatModelDocument) -> None:
    if not doc.threats:
        return
    _append_section(lines, "Ameaças")
    items: list[str] = []
    for t in doc.threats:
        risk = ""
        if t.risk:
            risk = f" — risco L×I={t.risk.likelihood}×{t.risk.impact}"
            if t.risk.score is not None:
                risk += f" (score {t.risk.score})"
        items.append(f"- **{t.title}** (`{t.id}`) [{t.stride.value}]{risk}")
    _append_bulleted(lines, items)


def _append_mitigations(lines: list[str], doc: ThreatModelDocument) -> None:
    if not doc.mitigations:
        return
    _append_section(lines, "Mitigações")
    _append_bulleted(
        lines,
        [f"- **{m.title}** (`{m.id}`) — {m.status.value}" for m in doc.mitigations],
    )


def export_document_markdown(doc: ThreatModelDocument) -> str:
    """Markdown simples: cabeçalho e secções na ordem canónica (ver testes em `test_exporters`)."""
    lines: list[str] = []
    _append_header(lines, doc)
    _append_business_context(lines, doc)
    _append_assets(lines, doc)
    _append_components(lines, doc)
    _append_data_flows(lines, doc)
    _append_trust_boundaries(lines, doc)
    _append_threats(lines, doc)
    _append_mitigations(lines, doc)

    return "\n".join(lines).rstrip() + "\n"
