"""Ligação entre resultados heurísticos e catálogo `otm_framework_mappings`."""

from __future__ import annotations

from collections import Counter

from otm_framework_mappings.registry import StrideFrameworkRegistry, default_stride_registry

from otm_threat_engine.result import AnalysisResult, HeuristicThreat


def _resolve_registry(registry: StrideFrameworkRegistry | None) -> StrideFrameworkRegistry:
    return registry or default_stride_registry()


def _count_framework_refs(heuristics: list[HeuristicThreat]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for h in heuristics:
        for ref in h.framework_refs:
            counts[ref.framework] += 1
    return dict(sorted(counts.items()))


def _enrich_heuristics_with_framework_refs(
    heuristics: list[HeuristicThreat],
    *,
    registry: StrideFrameworkRegistry,
) -> list[HeuristicThreat]:
    return [enrich_heuristic_threat(h, registry=registry) for h in heuristics]


def enrich_heuristic_threat(
    h: HeuristicThreat,
    registry: StrideFrameworkRegistry | None = None,
) -> HeuristicThreat:
    reg = _resolve_registry(registry)
    refs = reg.refs_for_stride(h.stride)
    if not refs:
        return h
    return h.model_copy(update={"framework_refs": refs})


def enrich_analysis_framework_refs(
    result: AnalysisResult,
    registry: StrideFrameworkRegistry | None = None,
) -> AnalysisResult:
    reg = _resolve_registry(registry)
    new_heuristics = _enrich_heuristics_with_framework_refs(result.heuristic_threats, registry=reg)
    summary = result.summary.model_copy(
        update={"framework_ref_counts_by_catalog": _count_framework_refs(new_heuristics)}
    )
    return result.model_copy(update={"heuristic_threats": new_heuristics, "summary": summary})
