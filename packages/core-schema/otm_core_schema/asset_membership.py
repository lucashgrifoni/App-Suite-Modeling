"""Ligação entre ativos e componentes, resolvida das duas direcções.

O schema deixa declarar a mesma ligação de dois lados e valida os dois: `Component.asset_ids` (do
lado do componente) e `Asset.related_component_ids` (do lado do ativo). Quem lê só um deles vê
metade dos modelos: uma lente que decide "há dados classificados neste componente" a partir de
`asset_ids` devolve zero para um documento que declarou a ligação no ativo, e devolve-o em
silêncio, porque o `otm validate` aceita as duas formas.

Mesma decisão, e mesma razão, que `trust_membership.resolve_component_boundaries`: uma resolução,
um sítio. Quem precisar dela chama daqui em vez de reimplementar a regra e voltar a ler um lado só.
"""

from __future__ import annotations

from otm_core_schema.document import ThreatModelDocument


def resolve_component_assets(doc: ThreatModelDocument) -> dict[str, set[str]]:
    """`component_id -> ids dos ativos que lhe pertencem`, juntando as duas formas de o declarar.

    As duas direcções **somam-se** em vez de uma vencer a outra: ao contrário da pertença a
    fronteiras, onde um componente está numa só, um componente pode legitimamente ter vários
    ativos declarados de maneiras diferentes. Componentes sem ativo nenhum não aparecem no mapa.
    """
    known_assets = {a.id for a in doc.assets}
    known_components = {c.id for c in doc.components}
    resolved: dict[str, set[str]] = {}

    for component in doc.components:
        linked = {aid for aid in (component.asset_ids or []) if aid in known_assets}
        if linked:
            resolved.setdefault(component.id, set()).update(linked)

    for asset in doc.assets:
        for cid in asset.related_component_ids or []:
            if cid in known_components:
                resolved.setdefault(cid, set()).add(asset.id)

    return resolved
