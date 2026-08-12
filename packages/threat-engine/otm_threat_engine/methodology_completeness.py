"""Avalia se o documento tem contexto suficiente para a metodologia escolhida."""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument, ThreatModelMethodology
from otm_core_schema.enums import MethodologyCompletenessState

from otm_threat_engine.methodology_lenses.common import looks_like_ai_context
from otm_threat_engine.methodology_lenses.linddun import _looks_like_pii_context
from otm_threat_engine.result import MethodologyCompletenessInfo


def _assess_pasta(doc: ThreatModelDocument) -> tuple[list[str], MethodologyCompletenessState]:
    bc = doc.business_context
    has_obj = bool(bc and (bc.business_objectives or bc.business_goals))
    has_assets = len(doc.assets) > 0
    reasons: list[str] = []
    if not has_obj:
        reasons.append("PASTA: faltam business_objectives ou business_goals explícitos.")
    if not has_assets:
        reasons.append("PASTA: sem ativos modelados — impacto operacional mal ancorado.")
    if not has_obj and not has_assets:
        return reasons, MethodologyCompletenessState.DEGRADED
    if not has_obj or not has_assets:
        return reasons, MethodologyCompletenessState.PARTIAL
    return reasons, MethodologyCompletenessState.COMPLETE


def _assess_nist_data_centric(doc: ThreatModelDocument) -> tuple[list[str], MethodologyCompletenessState]:
    if len(doc.assets) == 0:
        return (
            ["NIST data-centric: sem ativos — análise centrada em dados limitada."],
            MethodologyCompletenessState.DEGRADED,
        )
    classified = sum(
        1
        for a in doc.assets
        if a.data_classification is not None
        or (a.sensitivity and a.sensitivity.lower() in ("confidential", "restricted", "internal"))
    )
    if classified == 0:
        return (
            ["NIST data-centric: ativos sem data_classification clara."],
            MethodologyCompletenessState.PARTIAL,
        )
    return [], MethodologyCompletenessState.COMPLETE


def _assess_stride(doc: ThreatModelDocument) -> tuple[list[str], MethodologyCompletenessState]:
    if not doc.trust_boundaries:
        return (
            ["STRIDE: sem trust boundaries — superfície e TMW degradados."],
            MethodologyCompletenessState.PARTIAL,
        )
    if len(doc.components) < 2:
        return (
            ["STRIDE: poucos componentes — cobertura de ameaças provavelmente incompleta."],
            MethodologyCompletenessState.PARTIAL,
        )
    return [], MethodologyCompletenessState.COMPLETE


def _assess_linddun(doc: ThreatModelDocument) -> tuple[list[str], MethodologyCompletenessState]:
    if not _looks_like_pii_context(doc):
        return (
            ["LINDDUN: sem sinais claros de PII/privacidade no texto ou nos ativos."],
            MethodologyCompletenessState.PARTIAL,
        )
    return [], MethodologyCompletenessState.COMPLETE


def _assess_plot4ai(doc: ThreatModelDocument) -> tuple[list[str], MethodologyCompletenessState]:
    # `import_signals_corpus` só existe em modelos vindos do import de artefactos, por isso um
    # modelo IA escrito à mão ficava eternamente PARTIAL enquanto a lente PLOT4ai gerava
    # ameaças sobre ele. O gate é o mesmo da lente — tal como `_assess_linddun` usa o de PII.
    if not looks_like_ai_context(doc):
        return (
            ["PLOT4AI: sem sinais de sistema de IA no modelo — camadas AI podem ficar sub-evidenciadas."],
            MethodologyCompletenessState.PARTIAL,
        )
    return [], MethodologyCompletenessState.COMPLETE


def _assess_inventory(
    doc: ThreatModelDocument, methodology: ThreatModelMethodology
) -> tuple[list[str], MethodologyCompletenessState]:
    if not doc.assets:
        return (
            [f"{methodology.value}: sem ativos declarados — foco em inventário degradado."],
            MethodologyCompletenessState.PARTIAL,
        )
    return [], MethodologyCompletenessState.COMPLETE


def assess_methodology_completeness(
    doc: ThreatModelDocument,
    methodology: ThreatModelMethodology,
) -> MethodologyCompletenessInfo:
    simple_assessors = {
        ThreatModelMethodology.PASTA: _assess_pasta,
        ThreatModelMethodology.NIST_DATA_CENTRIC: _assess_nist_data_centric,
        ThreatModelMethodology.STRIDE: _assess_stride,
        ThreatModelMethodology.LINDDUN: _assess_linddun,
        ThreatModelMethodology.PLOT4AI: _assess_plot4ai,
    }
    assessor = simple_assessors.get(methodology)
    if assessor is not None:
        reasons, state = assessor(doc)
    elif methodology in {ThreatModelMethodology.OCTAVE_ALLEGRO, ThreatModelMethodology.CIA_DIE}:
        reasons, state = _assess_inventory(doc, methodology)
    else:  # pragma: no cover - unreachable: every ThreatModelMethodology is handled above
        reasons, state = [], MethodologyCompletenessState.COMPLETE

    note = None
    if state != MethodologyCompletenessState.COMPLETE:
        note = (
            "A metodologia foi aplicada com contexto incompleto; interpretar achados como orientação, "
            "não como cobertura total."
        )

    return MethodologyCompletenessInfo(state=state, reasons=reasons, note=note)
