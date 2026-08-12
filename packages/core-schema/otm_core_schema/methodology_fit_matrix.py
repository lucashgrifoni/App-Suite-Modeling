"""
Matriz de adequação: metodologia × contexto do modelo (strong / partial / weak).

Usada no pré-check e em relatórios — heurística, não garantia de cobertura.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from otm_core_schema.ai_context import looks_like_ai_context
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


@dataclass(frozen=True)
class _FitContext:
    has_assets: bool
    has_boundaries: bool
    has_obj: bool
    has_privacy_cue: bool
    classified: int
    flow_rich: float
    asset_count: int
    has_import_signals: bool
    has_ai_context: bool


def _build_fit_context(doc: ThreatModelDocument) -> _FitContext:
    bc = doc.business_context
    has_privacy_cue = bool(
        bc
        and (
            (bc.description and any(x in bc.description.lower() for x in ("pii", "lgpd", "gdpr", "dados pessoais")))
            or (bc.regulatory_context and "priv" in bc.regulatory_context.lower())
        )
    )
    return _FitContext(
        has_assets=len(doc.assets) > 0,
        has_boundaries=len(doc.trust_boundaries) > 0,
        has_obj=bool(bc and (bc.business_objectives or bc.business_goals)),
        has_privacy_cue=has_privacy_cue,
        classified=_classified_assets_count(doc),
        flow_rich=_rich_flow_ratio(doc),
        asset_count=len(doc.assets),
        has_import_signals=bool(doc.import_signals_corpus),
        has_ai_context=looks_like_ai_context(doc),
    )


def _fit_stride(c: _FitContext) -> FitLevel:
    if c.has_assets and c.has_boundaries and c.flow_rich >= 0.34:
        return "strong"
    return "partial" if (c.has_assets or c.has_boundaries) else "weak"


def _fit_pasta(c: _FitContext) -> FitLevel:
    if c.has_obj and c.has_assets and c.classified > 0:
        return "strong"
    return "partial" if (c.has_obj or c.has_assets) else "weak"


def _fit_nist(c: _FitContext) -> FitLevel:
    if not c.has_assets:
        return "weak"
    if c.classified >= max(1, c.asset_count // 2):
        return "strong"
    return "partial" if c.classified > 0 else "weak"


def _fit_linddun(c: _FitContext) -> FitLevel:
    if c.has_privacy_cue and c.has_assets:
        return "strong"
    return "partial" if (c.has_privacy_cue or c.has_assets) else "weak"


def _fit_plot4ai(c: _FitContext) -> FitLevel:
    # `has_import_signals` sozinho nunca chegava a "strong" e só fica verdadeiro em modelos
    # vindos do import de artefactos — um modelo escrito à mão não tinha alvo nenhum para
    # melhorar. O sinal certo é o mesmo que abre a lente PLOT4ai: se o motor considera isto
    # um sistema de IA, a matriz não pode dizer o contrário.
    if c.has_ai_context and c.has_assets and c.has_boundaries:
        return "strong"
    if c.has_ai_context or c.has_import_signals:
        return "partial"
    return "weak"


def _fit_octave(c: _FitContext) -> FitLevel:
    if c.has_obj and c.has_assets and c.classified >= max(1, min(2, c.asset_count // 2)):
        return "strong"
    return "partial" if (c.has_assets or c.has_obj) else "weak"


def _fit_cia(c: _FitContext) -> FitLevel:
    if c.has_boundaries and c.has_assets:
        return "strong"
    return "partial" if (c.has_boundaries or c.has_assets) else "weak"


_FIT_FUNCS = {
    ThreatModelMethodology.STRIDE: _fit_stride,
    ThreatModelMethodology.PASTA: _fit_pasta,
    ThreatModelMethodology.NIST_DATA_CENTRIC: _fit_nist,
    ThreatModelMethodology.LINDDUN: _fit_linddun,
    ThreatModelMethodology.PLOT4AI: _fit_plot4ai,
    ThreatModelMethodology.OCTAVE_ALLEGRO: _fit_octave,
    ThreatModelMethodology.CIA_DIE: _fit_cia,
}


def _fit_from_context(ctx: _FitContext, methodology: ThreatModelMethodology) -> FitLevel:
    fn = _FIT_FUNCS.get(methodology)
    if fn is not None:
        return fn(ctx)
    # Demais metodologias: conservador
    return "partial" if (ctx.has_assets and ctx.has_boundaries) else "weak"  # pragma: no cover - unreachable


def fit_for_methodology(
    doc: ThreatModelDocument,
    methodology: ThreatModelMethodology,
) -> FitLevel:
    """
    Avalia se o documento tem contexto suficiente para a metodologia indicada.
    """
    return _fit_from_context(_build_fit_context(doc), methodology)


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
    # Contexto construído uma vez: `has_ai_context` percorre o documento inteiro para montar
    # o corpus lexical, e sete chamadas a `fit_for_methodology` faziam-no sete vezes.
    ctx = _build_fit_context(doc)
    return {m.value: _fit_from_context(ctx, m) for m in keys}
