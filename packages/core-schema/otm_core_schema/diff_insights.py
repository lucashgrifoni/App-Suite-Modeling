"""
Insights explicativos a partir do diff estrutural e dos documentos.

Mantido em `core-schema` (sem dependência do motor) — texto útil para humanos e pipelines.
"""

from __future__ import annotations

from otm_core_schema.diff import ThreatModelDiff
from otm_core_schema.document import Component, DataFlow, ThreatModelDocument
from otm_core_schema.enums import ComponentKind


def _comp_by_id(doc: ThreatModelDocument) -> dict[str, Component]:
    return {c.id: c for c in doc.components}


def _flow_by_id(doc: ThreatModelDocument) -> dict[str, DataFlow]:
    return {f.id: f for f in doc.data_flows}


def _boundary_names(doc: ThreatModelDocument) -> dict[str, str]:
    return {b.id: b.name for b in doc.trust_boundaries}


def structural_key_insights(
    baseline: ThreatModelDocument,
    revised: ThreatModelDocument,
    d: ThreatModelDiff,
) -> list[str]:
    """
    Gera frases curtas explicando *por que* a mudança importa (risco / arquitetura).

    Não substitui análise heurística; contextualiza o diff estrutural.
    """
    insights: list[str] = []
    _comp_by_id(baseline)
    r_comp = _comp_by_id(revised)
    _flow_by_id(baseline)
    r_flow = _flow_by_id(revised)
    r_bn = _boundary_names(revised)
    b_bn = _boundary_names(baseline)

    for fid in d.model_info:
        if fid.field == "methodology":
            insights.append(
                f"Metodologia declarada no modelo alterou: {fid.before} → {fid.after}. "
                "Reavalie análise e relatórios com a nova lens."
            )
        elif fid.field == "industry_sector":
            insights.append(
                f"Setor do modelo alterou ({fid.before} → {fid.after}); packs e contexto regulatório podem divergir."
            )

    for tid in d.data_flows.added:
        fl = r_flow.get(tid)
        if not fl:
            continue
        fc = r_comp.get(fl.from_component)
        tc = r_comp.get(fl.to_component)
        fb = fc.in_trust_boundary if fc else None
        tb = tc.in_trust_boundary if tc else None
        if fb and tb and fb != tb:
            insights.append(
                f"Novo fluxo `{tid}` cruza fronteiras ({r_bn.get(fb, fb)} → {r_bn.get(tb, tb)}); "
                "rever exposição e controlos de confiança."
            )
        elif fc and fc.kind == ComponentKind.EXTERNAL_ENTITY:
            insights.append(
                f"Novo fluxo `{tid}` envolve entidade externa `{fl.from_component}` ou `{fl.to_component}`; "
                "superfície de ataque pode ter aumentado."
            )

    for cid in d.components.added:
        c = r_comp.get(cid)
        if not c:
            continue
        if c.kind == ComponentKind.USER and c.in_trust_boundary:
            insights.append(
                f"Novo componente utilizador `{cid}` na fronteira `{c.in_trust_boundary}`; "
                "ver autenticação e superfície exposta à Internet."
            )
        if c.kind == ComponentKind.EXTERNAL_ENTITY:
            insights.append(
                f"Nova entidade externa `{cid}`; integrações e webhook devem ser reverificadas."
            )

    for ment in d.trust_boundaries.modified:
        name = r_bn.get(ment.id, ment.id)
        insights.append(
            f"Fronteira `{name}` (`{ment.id}`) foi alterada (membros ou metadados); "
            "revalidar fluxos que a atravessam."
        )
    for bid in d.trust_boundaries.added:
        insights.append(f"Nova trust boundary `{r_bn.get(bid, bid)}` (`{bid}`); mapear fluxos que a cruzam.")
    for bid in d.trust_boundaries.removed:
        insights.append(f"Trust boundary `{b_bn.get(bid, bid)}` (`{bid}`) removida; rede de confiança mudou.")

    for aid in d.assets.added:
        insights.append(
            f"Novo ativo `{aid}`; ver classificação, retenção e fluxos que o processam."
        )
    for t in d.threats.added:
        insights.append(f"Nova ameaça canónica no documento (`{t}`); priorizar tratamento no backlog.")
    for t in d.threats.removed:
        insights.append(f"Ameaça canónica `{t}` removida; confirmar fechamento ou risco aceite documentado.")

    for m in d.mitigations.modified:
        for ch in m.changes:
            if ch.field == "status":
                insights.append(
                    f"Mitigação `{m.id}` mudou de estado; rever cobertura de ameaças ligadas."
                )
                break

    if d.residual_risk_summary:
        insights.append("Resumo de risco residual ao nível do documento foi atualizado.")

    # dedupe preservando ordem
    seen: set[str] = set()
    unique: list[str] = []
    for s in insights:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    return unique
