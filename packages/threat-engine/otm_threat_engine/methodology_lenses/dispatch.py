from __future__ import annotations

from collections.abc import Callable

from otm_core_schema import ThreatModelDocument, ThreatModelMethodology

from otm_threat_engine.methodology_lenses.common import append_engine_lens_note
from otm_threat_engine.methodology_lenses.linddun import apply_linddun_lens
from otm_threat_engine.methodology_lenses.nist_data_centric import apply_nist_data_centric_lens
from otm_threat_engine.methodology_lenses.pasta import apply_pasta_lens
from otm_threat_engine.methodology_lenses.plot4ai import apply_plot4ai_lens
from otm_threat_engine.result import AnalysisResult

LensHandler = Callable[[ThreatModelDocument, AnalysisResult], AnalysisResult]


def build_lens_dispatch() -> dict[ThreatModelMethodology, LensHandler]:
    return {
        ThreatModelMethodology.STRIDE: _apply_stride_lens,
        ThreatModelMethodology.LINDDUN: apply_linddun_lens,
        ThreatModelMethodology.NIST_DATA_CENTRIC: _apply_nist_lens,
        ThreatModelMethodology.OCTAVE_ALLEGRO: _apply_octave_lens,
        ThreatModelMethodology.CIA_DIE: _apply_cia_die_lens,
        ThreatModelMethodology.PASTA: apply_pasta_lens,
        ThreatModelMethodology.PLOT4AI: apply_plot4ai_lens,
    }


def _apply_stride_lens(doc: ThreatModelDocument, result: AnalysisResult) -> AnalysisResult:
    _ = doc
    return result


def _apply_nist_lens(doc: ThreatModelDocument, result: AnalysisResult) -> AnalysisResult:
    _ = doc
    return apply_nist_data_centric_lens(result)


def _apply_octave_lens(doc: ThreatModelDocument, result: AnalysisResult) -> AnalysisResult:
    _ = doc
    return append_engine_lens_note(
        result,
        methodology=ThreatModelMethodology.OCTAVE_ALLEGRO,
        note="Lente OCTAVE Allegro aplicada: priorize ativos críticos e risco de negócio.",
    )


def _apply_cia_die_lens(doc: ThreatModelDocument, result: AnalysisResult) -> AnalysisResult:
    _ = doc
    active = [h for h in result.heuristic_threats if not h.skipped_as_duplicate]
    active_sorted = sorted(active, key=lambda h: h.risk.score or 0.0, reverse=True)[:10]
    keep_ids = {h.id for h in active_sorted}
    concise = [h for h in result.heuristic_threats if h.skipped_as_duplicate or h.id in keep_ids]
    out = result.model_copy(update={"heuristic_threats": concise})
    return append_engine_lens_note(
        out,
        methodology=ThreatModelMethodology.CIA_DIE,
        note="Lente CIA/CIA-DIE aplicada: resumo simplificado com ameaças de maior impacto.",
    )
