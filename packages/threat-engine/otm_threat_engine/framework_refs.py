"""Ligação entre resultados heurísticos e catálogo `otm_framework_mappings`."""

from __future__ import annotations

from collections import Counter

from otm_framework_mappings.registry import StrideFrameworkRegistry, default_stride_registry

from otm_threat_engine.result import AnalysisResult, HeuristicThreat


def enrich_heuristic_threat(
    h: HeuristicThreat,
    registry: StrideFrameworkRegistry | None = None,
) -> HeuristicThreat:
    reg = registry or default_stride_registry()
    refs = reg.refs_for_stride(h.stride)
    if not refs:
        return h
    return h.model_copy(update={"framework_refs": refs})


def enrich_analysis_framework_refs(
    result: AnalysisResult,
    registry: StrideFrameworkRegistry | None = None,
) -> AnalysisResult:
    reg = registry or default_stride_registry()
    new_heuristics = [enrich_heuristic_threat(h, registry=reg) for h in result.heuristic_threats]
    counts: Counter[str] = Counter()
    for h in new_heuristics:
        for ref in h.framework_refs:
            counts[ref.framework] += 1
    summary = result.summary.model_copy(
        update={"framework_ref_counts_by_catalog": dict(sorted(counts.items()))}
    )
    return result.model_copy(update={"heuristic_threats": new_heuristics, "summary": summary})
