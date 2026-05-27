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


def _model_info_insights(d: ThreatModelDiff) -> list[str]:
    out: list[str] = []
    for fid in d.model_info:
        if fid.field == "methodology":
            out.append(
                f"Metodologia declarada no modelo alterou: {fid.before} → {fid.after}. "
                "Reavalie análise e relatórios com a nova lens."
            )
        elif fid.field == "industry_sector":
            out.append(
                f"Setor do modelo alterou ({fid.before} → {fid.after}); packs e contexto regulatório podem divergir."
            )
    return out


def _flow_added_insights(
    d: ThreatModelDiff,
    r_flow: dict[str, DataFlow],
    r_comp: dict[str, Component],
    r_bn: dict[str, str],
) -> list[str]:
    out: list[str] = []
    for tid in d.data_flows.added:
        fl = r_flow.get(tid)
        if not fl:
            continue  # pragma: no cover - defensive guard
        fc = r_comp.get(fl.from_component)
        tc = r_comp.get(fl.to_component)
        fb = fc.in_trust_boundary if fc else None
        tb = tc.in_trust_boundary if tc else None
        if fb and tb and fb != tb:
            out.append(
                f"Novo fluxo `{tid}` cruza fronteiras ({r_bn.get(fb, fb)} → {r_bn.get(tb, tb)}); "
                "rever exposição e controlos de confiança."
            )
        elif fc and fc.kind == ComponentKind.EXTERNAL_ENTITY:
            out.append(
                f"Novo fluxo `{tid}` envolve entidade externa `{fl.from_component}` ou `{fl.to_component}`; "
                "superfície de ataque pode ter aumentado."
            )
    return out


def _component_added_insights(d: ThreatModelDiff, r_comp: dict[str, Component]) -> list[str]:
    out: list[str] = []
    for cid in d.components.added:
        c = r_comp.get(cid)
        if not c:
            continue  # pragma: no cover - defensive guard
        if c.kind == ComponentKind.USER and c.in_trust_boundary:
            out.append(
                f"Novo componente utilizador `{cid}` na fronteira `{c.in_trust_boundary}`; "
                "ver autenticação e superfície exposta à Internet."
            )
        if c.kind == ComponentKind.EXTERNAL_ENTITY:
            out.append(f"Nova entidade externa `{cid}`; integrações e webhook devem ser reverificadas.")
    return out


def _boundary_insights(d: ThreatModelDiff, r_bn: dict[str, str], b_bn: dict[str, str]) -> list[str]:
    out: list[str] = []
    for ment in d.trust_boundaries.modified:
        name = r_bn.get(ment.id, ment.id)
        out.append(
            f"Fronteira `{name}` (`{ment.id}`) foi alterada (membros ou metadados); revalidar fluxos que a atravessam."
        )
    for bid in d.trust_boundaries.added:
        out.append(f"Nova trust boundary `{r_bn.get(bid, bid)}` (`{bid}`); mapear fluxos que a cruzam.")
    for bid in d.trust_boundaries.removed:
        out.append(f"Trust boundary `{b_bn.get(bid, bid)}` (`{bid}`) removida; rede de confiança mudou.")
    return out


def _asset_threat_insights(d: ThreatModelDiff) -> list[str]:
    out: list[str] = []
    for aid in d.assets.added:
        out.append(f"Novo ativo `{aid}`; ver classificação, retenção e fluxos que o processam.")
    for t in d.threats.added:
        out.append(f"Nova ameaça canónica no documento (`{t}`); priorizar tratamento no backlog.")
    for t in d.threats.removed:
        out.append(f"Ameaça canónica `{t}` removida; confirmar fechamento ou risco aceite documentado.")
    return out


def _mitigation_change_insights(d: ThreatModelDiff) -> list[str]:
    out: list[str] = []
    for m in d.mitigations.modified:
        for ch in m.changes:
            if ch.field == "status":
                out.append(f"Mitigação `{m.id}` mudou de estado; rever cobertura de ameaças ligadas.")
                break
    return out


def structural_key_insights(
    baseline: ThreatModelDocument,
    revised: ThreatModelDocument,
    d: ThreatModelDiff,
) -> list[str]:
    """
    Gera frases curtas explicando *por que* a mudança importa (risco / arquitetura).

    Não substitui análise heurística; contextualiza o diff estrutural.
    """
    r_comp = _comp_by_id(revised)
    r_flow = _flow_by_id(revised)
    r_bn = _boundary_names(revised)
    b_bn = _boundary_names(baseline)

    insights: list[str] = []
    insights.extend(_model_info_insights(d))
    insights.extend(_flow_added_insights(d, r_flow, r_comp, r_bn))
    insights.extend(_component_added_insights(d, r_comp))
    insights.extend(_boundary_insights(d, r_bn, b_bn))
    insights.extend(_asset_threat_insights(d))
    insights.extend(_mitigation_change_insights(d))

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
