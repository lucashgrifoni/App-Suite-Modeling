"""Pertença de componentes a fronteiras de confiança, resolvida das duas direcções.

O schema deixa declarar a mesma coisa de dois lados e valida os dois: `Component.in_trust_boundary`
(do lado do componente) e `TrustBoundary.member_component_ids` (do lado da fronteira). O import
de artefactos chega a derivar o segundo a partir do primeiro, mas nada derivava o inverso — e o
motor só lia o lado do componente. Um modelo escrito pelo lado da fronteira passava no
`otm validate` e depois não produzia travessia de fronteira nenhuma, em silêncio.

Uma resolução, um sítio. Quem precisa dela (heurísticas, insights, anti-padrões, avisos
estruturais) chama daqui em vez de reimplementar a regra.
"""

from __future__ import annotations

from otm_core_schema.document import ThreatModelDocument


def resolve_component_boundaries(doc: ThreatModelDocument) -> dict[str, str]:
    """`component_id -> boundary_id`, juntando as duas formas de o declarar.

    Quando as duas discordam, o lado do componente ganha: é a declaração mais específica e é a
    que o motor sempre respeitou, por isso modelos existentes não mudam de resultado. A
    discordância não fica escondida — `boundary_membership_conflicts` reporta-a.
    """
    known = {c.id for c in doc.components}
    resolved: dict[str, str] = {}
    for tb in doc.trust_boundaries:
        for cid in tb.member_component_ids:
            if cid in known:
                # `setdefault`: se duas fronteiras reclamam o mesmo componente, vence a
                # primeira em ordem de documento — determinístico, e reportado como conflito.
                resolved.setdefault(cid, tb.id)
    for c in doc.components:
        if c.in_trust_boundary:
            resolved[c.id] = c.in_trust_boundary
    return resolved


def boundary_membership_conflicts(doc: ThreatModelDocument) -> dict[str, list[str]]:
    """`component_id -> fronteiras distintas que o reclamam`, só para os que têm mais de uma.

    Ordem estável: primeiro o que o componente declara, depois as fronteiras por ordem de
    documento.
    """
    known = {c.id for c in doc.components}
    claims: dict[str, list[str]] = {}
    for c in doc.components:
        if c.in_trust_boundary:
            claims[c.id] = [c.in_trust_boundary]
    for tb in doc.trust_boundaries:
        for cid in tb.member_component_ids:
            if cid in known and tb.id not in claims.setdefault(cid, []):
                claims[cid].append(tb.id)
    return {cid: boundaries for cid, boundaries in claims.items() if len(boundaries) > 1}


def cross_boundary_flow_ids(doc: ThreatModelDocument) -> set[str]:
    """Ids dos fluxos que ligam duas fronteiras distintas."""
    boundaries = resolve_component_boundaries(doc)
    ids: set[str] = set()
    for flow in doc.data_flows:
        origin = boundaries.get(flow.from_component)
        target = boundaries.get(flow.to_component)
        if origin and target and origin != target:
            ids.add(flow.id)
    return ids
