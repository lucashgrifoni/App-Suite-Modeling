"""
Matriz de adequação: metodologia × contexto do modelo (strong / partial / weak).

Usada no pré-check e em relatórios — heurística, não garantia de cobertura.
"""

from __future__ import annotations

from typing import Literal

from otm_core_schema.document import ThreatModelDocument
from otm_core_schema.enums import ThreatModelMethodology

FitLevel = Literal["strong", "partial", "weak"]


def _classified_assets_count(doc: ThreatModelDocument) -> int:
    return sum(
        1
        for a in doc.assets
        if a.data_classification is not None or (a.sensitivity and len((a.sensitivity or "").strip()) > 2)
    )


def _rich_flow_ratio(doc: ThreatModelDocument) -> float:
    if not doc.data_flows:
        return 0.0
    rich = sum(
        1
        for f in doc.data_flows
        if f.semantic_class.value != "generic"
        or f.public_exposure is not None
        or (f.data_types and len(f.data_types) > 0)
    )
    return rich / max(1, len(doc.data_flows))


def fit_for_methodology(
    doc: ThreatModelDocument,
    methodology: ThreatModelMethodology,
) -> FitLevel:
    """
    Avalia se o documento tem contexto suficiente para a metodologia indicada.
    """
    has_assets = len(doc.assets) > 0
    has_boundaries = len(doc.trust_boundaries) > 0
    bc = doc.business_context
    has_obj = bool(bc and (bc.business_objectives or bc.business_goals))
    has_privacy_cue = bool(
        bc
        and (
            (bc.description and any(x in bc.description.lower() for x in ("pii", "lgpd", "gdpr", "dados pessoais")))
            or (bc.regulatory_context and "priv" in bc.regulatory_context.lower())
        )
    )
    classified = _classified_assets_count(doc)
    flow_rich = _rich_flow_ratio(doc)

    if methodology == ThreatModelMethodology.STRIDE:
        if has_assets and has_boundaries and flow_rich >= 0.34:
            return "strong"
        if has_assets or has_boundaries:
            return "partial"
        return "weak"

    if methodology == ThreatModelMethodology.PASTA:
        if has_obj and has_assets and classified > 0:
            return "strong"
        if has_obj or has_assets:
            return "partial"
        return "weak"

    if methodology == ThreatModelMethodology.NIST_DATA_CENTRIC:
        if not has_assets:
            return "weak"
        if classified >= max(1, len(doc.assets) // 2):
            return "strong"
        if classified > 0:
            return "partial"
        return "weak"

    if methodology == ThreatModelMethodology.LINDDUN:
        if has_privacy_cue and has_assets:
            return "strong"
        if has_privacy_cue or has_assets:
            return "partial"
        return "weak"

    if methodology == ThreatModelMethodology.PLOT4AI:
        return "partial" if doc.import_signals_corpus else "weak"

    if methodology == ThreatModelMethodology.OCTAVE_ALLEGRO:
        if has_obj and has_assets and classified >= max(1, min(2, len(doc.assets) // 2)):
            return "strong"
        if has_assets and has_obj:
            return "partial"
        if has_assets or has_obj:
            return "partial"
        return "weak"

    if methodology == ThreatModelMethodology.CIA_DIE:
        if has_boundaries and has_assets:
            return "strong"
        if has_boundaries or has_assets:
            return "partial"
        return "weak"

    # Demais metodologias: conservador
    return "partial" if (has_assets and has_boundaries) else "weak"


def build_methodology_fit_matrix(doc: ThreatModelDocument) -> dict[str, str]:
    """Mapa metodologia (valor enum) → fit (strong|partial|weak)."""
    keys = (
        ThreatModelMethodology.STRIDE,
        ThreatModelMethodology.PASTA,
        ThreatModelMethodology.NIST_DATA_CENTRIC,
        ThreatModelMethodology.LINDDUN,
        ThreatModelMethodology.PLOT4AI,
        ThreatModelMethodology.OCTAVE_ALLEGRO,
        ThreatModelMethodology.CIA_DIE,
    )
    return {m.value: fit_for_methodology(doc, m) for m in keys}
