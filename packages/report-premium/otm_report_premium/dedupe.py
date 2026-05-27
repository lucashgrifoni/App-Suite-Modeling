"""Agrupamento de ameaças semelhantes por causa raiz e assinatura leve."""

from __future__ import annotations

from collections import defaultdict

from otm_core_schema import ThreatModelMethodology
from otm_core_schema.document import ThreatModelDocument
from otm_threat_engine.remediation.classify import classify_threat
from otm_threat_engine.result import HeuristicThreat

from .models import DedupeGroup


def build_dedupe_groups(
    threats: list[HeuristicThreat],
    methodology: ThreatModelMethodology,
    doc: ThreatModelDocument | None,
) -> list[DedupeGroup]:
    """
    Agrupa por (grouped_root_cause, stride) vindo de classify_threat.
    """
    buckets: dict[str, list[HeuristicThreat]] = defaultdict(list)
    keys_display: dict[str, str] = {}

    for t in threats:
        if t.skipped_as_duplicate:
            continue  # pragma: no cover - defensive guard
        root, _ctrl, _cat, _layer = classify_threat(t, doc, methodology)
        key = f"{root}|{t.stride.value}"
        buckets[key].append(t)
        keys_display[key] = root

    out: list[DedupeGroup] = []
    for key, items in sorted(buckets.items(), key=lambda x: -len(x[1])):
        if len(items) < 2:
            continue
        comps: list[str] = []
        for t in items:
            if t.target_component_id:
                comps.append(t.target_component_id)
        unified = (
            f"Correção transversal para causa `{keys_display[key]}`: aplicar controlos "
            f"no catálogo associado e rever componentes: {', '.join(sorted(set(comps))[:8])}."
        )
        out.append(
            DedupeGroup(
                group_key=key,
                occurrence_count=len(items),
                threat_ids=[t.id for t in items],
                components=sorted(set(comps)),
                unified_remediation=unified,
            )
        )
    return out[:25]
