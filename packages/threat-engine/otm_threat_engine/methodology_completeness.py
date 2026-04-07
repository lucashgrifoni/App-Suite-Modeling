"""Avalia se o documento tem contexto suficiente para a metodologia escolhida."""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument, ThreatModelMethodology
from otm_core_schema.enums import MethodologyCompletenessState

from otm_threat_engine.methodology_lenses.linddun import _looks_like_pii_context
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

    if methodology == ThreatModelMethodology.STRIDE:
        if not doc.trust_boundaries:
            reasons.append("STRIDE: sem trust boundaries — superfície e TMW degradados.")
            state = MethodologyCompletenessState.PARTIAL
        elif len(doc.components) < 2:
            reasons.append("STRIDE: poucos componentes — cobertura de ameaças provavelmente incompleta.")
            state = MethodologyCompletenessState.PARTIAL

    if methodology == ThreatModelMethodology.LINDDUN:
        if not _looks_like_pii_context(doc):
            reasons.append("LINDDUN: sem sinais claros de PII/privacidade no texto ou nos ativos.")
            state = MethodologyCompletenessState.PARTIAL

    if methodology == ThreatModelMethodology.PLOT4AI and not doc.import_signals_corpus:
        reasons.append("PLOT4AI: sem corpus/import_signals — camadas AI podem ficar sub-evidenciadas.")
        state = MethodologyCompletenessState.PARTIAL

    if methodology in {ThreatModelMethodology.OCTAVE_ALLEGRO, ThreatModelMethodology.CIA_DIE}:
        if not doc.assets:
            reasons.append(f"{methodology.value}: sem ativos declarados — foco em inventário degradado.")
            state = MethodologyCompletenessState.PARTIAL

    note = None
    if state != MethodologyCompletenessState.COMPLETE:
        note = (
            "A metodologia foi aplicada com contexto incompleto; interpretar achados como orientação, "
            "não como cobertura total."
        )

    return MethodologyCompletenessInfo(state=state, reasons=reasons, note=note)
