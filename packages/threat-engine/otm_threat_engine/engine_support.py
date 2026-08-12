from __future__ import annotations

from otm_core_schema import ThreatModelDocument

# A pertença a fronteiras resolve-se em core-schema porque se declara de dois lados
# (`Component.in_trust_boundary` e `TrustBoundary.member_component_ids`) e havia três cópias
# desta regra no motor, todas a ler só um dos lados. Reexportado com o nome histórico.
from otm_core_schema.trust_membership import cross_boundary_flow_ids
from otm_industry_packs.models import PackDefinition

from otm_threat_engine.pack_runtime import ID_PREFIX as PACK_ID_PREFIX
from otm_threat_engine.pack_runtime import iter_pack_heuristic_threats
from otm_threat_engine.result import AnalysisResult, AnalysisSummary, HeuristicThreat

__all__ = [
    "build_analysis_summary",
    "cross_boundary_flow_ids",
    "existing_threat_keys",
    "extend_with_pack_heuristics",
    "recompute_summary_with_methodology",
]


def existing_threat_keys(doc: ThreatModelDocument) -> set[tuple[str | None, str | None, str]]:
    keys: set[tuple[str | None, str | None, str]] = set()
    for t in doc.threats:
        keys.add((t.target_component_id, t.target_data_flow_id, t.stride.value))
    return keys


def _active_risk_scores(heuristics: list[HeuristicThreat]) -> list[float]:
    return [h.risk.score for h in heuristics if not h.skipped_as_duplicate and h.risk.score is not None]


def _is_pack_threat(h: HeuristicThreat) -> bool:
    return h.id.startswith(f"{PACK_ID_PREFIX}_")


def recompute_summary_with_methodology(result: AnalysisResult) -> AnalysisResult:
    """Reconta o sumário depois de a lente metodológica mexer na lista de heurísticas.

    A lente só acrescenta heurísticas base (e ajusta impactos), mas os contadores base e de
    pack são apresentados lado a lado como números **disjuntos** — o painel do CLI, o Markdown
    e a grelha de métricas da UI escrevem "Base heuristics: N" ao lado de "pack threats: M".
    Recontar tudo para o campo base fazia N incluir M e os dois deixavam de somar ao tamanho
    da lista de ameaças. A divisão do builder tem de sobreviver à recontagem.
    """
    active = [h for h in result.heuristic_threats if not h.skipped_as_duplicate]
    skipped = [h for h in result.heuristic_threats if h.skipped_as_duplicate]
    active_scores = _active_risk_scores(result.heuristic_threats)
    pack_active = sum(1 for h in active if _is_pack_threat(h))
    pack_skipped = sum(1 for h in skipped if _is_pack_threat(h))
    summary = result.summary.model_copy(
        update={
            "heuristic_threats_generated": len(active) - pack_active,
            "heuristic_threats_skipped_duplicate": len(skipped) - pack_skipped,
            "pack_threats_generated": pack_active,
            "pack_threats_skipped_duplicate": pack_skipped,
            "max_risk_score": max(active_scores) if active_scores else None,
        }
    )
    return result.model_copy(update={"summary": summary})


def extend_with_pack_heuristics(
    *,
    doc: ThreatModelDocument,
    heuristics: list[HeuristicThreat],
    covered: set[tuple[str | None, str | None, str]],
    pack: PackDefinition | None,
) -> tuple[int, int, list[str]]:
    if pack is None:
        return 0, 0, []
    pack_hints = list(pack.control_hints)
    pack_heuristics, pack_skip = iter_pack_heuristic_threats(doc, pack, covered)
    heuristics.extend(pack_heuristics)
    pack_gen = sum(1 for h in pack_heuristics if not h.skipped_as_duplicate)
    return pack_gen, pack_skip, pack_hints


def build_analysis_summary(
    *,
    structural_count: int,
    trust_count: int,
    heuristics: list[HeuristicThreat],
    base_skipped: int,
    pack_gen: int,
    pack_skip: int,
) -> AnalysisSummary:
    base_generated = sum(1 for h in heuristics if not h.skipped_as_duplicate) - pack_gen
    active_scores = _active_risk_scores(heuristics)
    return AnalysisSummary(
        structural_findings=structural_count,
        trust_boundary_findings=trust_count,
        heuristic_threats_generated=base_generated,
        heuristic_threats_skipped_duplicate=base_skipped,
        pack_threats_generated=pack_gen,
        pack_threats_skipped_duplicate=pack_skip,
        max_risk_score=max(active_scores) if active_scores else None,
    )
