"""Integração opcional de ameaças heurísticas no documento canônico (persistência TaC)."""

from __future__ import annotations

from copy import deepcopy

from otm_core_schema import Threat, ThreatModelDocument, TreatmentStatus

from otm_threat_engine.result import HeuristicThreat


def merge_heuristic_threats(
    doc: ThreatModelDocument,
    threats: list[HeuristicThreat],
    *,
    only_new: bool = True,
) -> ThreatModelDocument:
    """
    Devolve uma **cópia** do documento com ameaças heurísticas acrescentadas.

    - `only_new=True`: ignora entradas com `skipped_as_duplicate=True`.
    - IDs de ameaça = `HeuristicThreat.id` (devem ser únicos face a `doc.threats`).
    """
    out = deepcopy(doc)
    existing_ids = {t.id for t in out.threats}

    for h in threats:
        if only_new and h.skipped_as_duplicate:
            continue
        if h.id in existing_ids:
            continue
        out.threats.append(
            Threat(
                id=h.id,
                title=h.title,
                description=h.description,
                stride=h.stride,
                target_component_id=h.target_component_id,
                target_data_flow_id=h.target_data_flow_id,
                target_asset_id=h.target_asset_id,
                risk=h.risk,
                treatment_status=TreatmentStatus.NEW,
                framework_refs=[*h.framework_refs],
                metadata={"source": "otm_threat_engine", "engine_heuristic": True},
            )
        )
        existing_ids.add(h.id)

    return out
