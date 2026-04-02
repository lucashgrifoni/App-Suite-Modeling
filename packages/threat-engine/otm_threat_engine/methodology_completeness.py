"""Avalia se o documento tem contexto suficiente para a metodologia escolhida."""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument, ThreatModelMethodology
from otm_core_schema.enums import MethodologyCompletenessState

from otm_threat_engine.result import MethodologyCompletenessInfo


def assess_methodology_completeness(
    doc: ThreatModelDocument,
    methodology: ThreatModelMethodology,
) -> MethodologyCompletenessInfo:
    reasons: list[str] = []
    state = MethodologyCompletenessState.COMPLETE

    if methodology == ThreatModelMethodology.PASTA:
        bc = doc.business_context
        has_obj = bool(bc and (bc.business_objectives or bc.business_goals))
        has_assets = len(doc.assets) > 0
        if not has_obj:
            reasons.append("PASTA: faltam business_objectives ou business_goals explícitos.")
        if not has_assets:
            reasons.append("PASTA: sem ativos modelados — impacto operacional mal ancorado.")
        if not has_obj and not has_assets:
            state = MethodologyCompletenessState.DEGRADED
        elif not has_obj or not has_assets:
            state = MethodologyCompletenessState.PARTIAL

    if methodology == ThreatModelMethodology.NIST_DATA_CENTRIC:
        if len(doc.assets) == 0:
            reasons.append("NIST data-centric: sem ativos — análise centrada em dados limitada.")
            state = MethodologyCompletenessState.DEGRADED
        else:
            classified = sum(
                1
                for a in doc.assets
                if a.data_classification is not None
                or (a.sensitivity and a.sensitivity.lower() in ("confidential", "restricted", "internal"))
            )
            if classified == 0:
                reasons.append("NIST data-centric: ativos sem data_classification clara.")
                state = MethodologyCompletenessState.PARTIAL

    note = None
    if state != MethodologyCompletenessState.COMPLETE:
        note = (
            "A metodologia foi aplicada com contexto incompleto; interpretar achados como orientação, "
            "não como cobertura total."
        )

    return MethodologyCompletenessInfo(state=state, reasons=reasons, note=note)
