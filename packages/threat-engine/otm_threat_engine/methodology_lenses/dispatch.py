from __future__ import annotations

from collections.abc import Callable

from otm_core_schema import ThreatModelDocument, ThreatModelMethodology

from otm_threat_engine.methodology_lenses.common import (
    append_engine_lens_note,
    append_methodology_insights,
)
from otm_threat_engine.methodology_lenses.linddun import apply_linddun_lens
from otm_threat_engine.methodology_lenses.nist_data_centric import apply_nist_data_centric_lens
from otm_threat_engine.methodology_lenses.pasta import apply_pasta_lens
from otm_threat_engine.methodology_lenses.plot4ai import apply_plot4ai_lens
from otm_threat_engine.result import AnalysisResult

LensHandler = Callable[[ThreatModelDocument, AnalysisResult], AnalysisResult]

#: Quantas ameaças activas a vista executiva CIA/CIA-DIE destaca.
CIA_DIE_HIGHLIGHT_COUNT = 10


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
    """Vista executiva CIA/CIA-DIE: destaca as de maior impacto **sem apagar as outras**.

    Esta lente era a única que *removia* heurísticas em vez de acrescentar. Ficava com as dez
    activas de maior score e reconstruía `heuristic_threats` a partir dessa selecção, e
    `recompute_summary_with_methodology` recontava o sumário sobre a lista já truncada — pelo
    que o próprio resultado deixava de registar que alguma coisa tinha sido descartada.

    O efeito não era cosmético. `skipped_as_duplicate` marca; isto **apagava**: as ameaças que
    caíam fora das dez desapareciam do `analyze.json`, do SARIF, do relatório premium, do
    backlog de remediação e do cockpit de risco — e, sobretudo, do conjunto que o gate de drift
    compara. Com os dois lados na mesma lente, `methodology_changed` não dispara e o caminho
    fail-closed do gate nunca corre: no exemplo SaaS que acompanha o projecto, um PR que
    acrescentava um datastore de PII fazia o gate falhar sob `stride` (3 ameaças HIGH novas) e
    passar limpo sob `cia_die`. Um veredito verde por truncagem é um gate que mente.

    "As dez de maior impacto" é uma escolha de *apresentação* legítima, e continua a ser feita —
    mas onde uma escolha de apresentação pertence: um bloco de `methodology_insights`, que o
    Markdown e a UI já renderizam. A análise que sai daqui é a análise completa.
    """
    _ = doc
    active = [h for h in result.heuristic_threats if not h.skipped_as_duplicate]
    highlighted = sorted(active, key=lambda h: h.risk.score or 0.0, reverse=True)[:CIA_DIE_HIGHLIGHT_COUNT]
    out = append_methodology_insights(
        result,
        profile="executivo/workshop — impacto sobre dados (CIA) e propriedades DIE",
        blocks=[
            (
                "cia_die_top_impact",
                f"Maior impacto ({len(highlighted)} de {len(active)} ameaças activas)",
                [f"[{h.risk.score:.0f}] {h.title}" if h.risk.score is not None else h.title for h in highlighted],
            )
        ],
    )
    return append_engine_lens_note(
        out,
        methodology=ThreatModelMethodology.CIA_DIE,
        note=(
            "Lente CIA/CIA-DIE aplicada: destaque executivo das ameaças de maior impacto. "
            "O conjunto completo de ameaças é preservado para exportação, diff e gate."
        ),
    )
