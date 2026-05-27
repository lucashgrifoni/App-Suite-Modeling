from __future__ import annotations

from otm_core_schema import ThreatModelDocument
from otm_industry_packs.models import PackDefinition

from otm_threat_engine.pack_runtime import iter_pack_heuristic_threats
from otm_threat_engine.result import AnalysisResult, AnalysisSummary, HeuristicThreat


def existing_threat_keys(doc: ThreatModelDocument) -> set[tuple[str | None, str | None, str]]:
    keys: set[tuple[str | None, str | None, str]] = set()
    for t in doc.threats:
        keys.add((t.target_component_id, t.target_data_flow_id, t.stride.value))
    return keys


def cross_boundary_flow_ids(doc: ThreatModelDocument) -> set[str]:
    ids = set()
    by_comp = {c.id: c for c in doc.components}
    for flow in doc.data_flows:
        a = by_comp.get(flow.from_component)
        b = by_comp.get(flow.to_component)
        if not a or not b:
            continue  # pragma: no cover - defensive: skip when an id is missing
        if a.in_trust_boundary and b.in_trust_boundary and a.in_trust_boundary != b.in_trust_boundary:
            ids.add(flow.id)
    return ids


def _active_risk_scores(heuristics: list[HeuristicThreat]) -> list[float]:
    return [h.risk.score for h in heuristics if not h.skipped_as_duplicate and h.risk.score is not None]


def recompute_summary_with_methodology(result: AnalysisResult) -> AnalysisResult:
    active = [h for h in result.heuristic_threats if not h.skipped_as_duplicate]
    active_scores = _active_risk_scores(result.heuristic_threats)
    summary = result.summary.model_copy(
        update={
            "heuristic_threats_generated": len(active),
            "heuristic_threats_skipped_duplicate": len(result.heuristic_threats) - len(active),
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
