"""Ligação entre resultados heurísticos e catálogo `otm_framework_mappings`.

Cada heurística recebe (1) os refs da sua categoria STRIDE (mapa principal) e,
adicionalmente, (2) refs específicos por id de heurística — a lente de IA que
liga as heurísticas `plot4ai_*` ao OWASP LLM Top 10 (2025) e ao MITRE ATLAS.
Ambos fluem pelo mesmo campo `framework_refs`, sem alteração de schema.
"""

from __future__ import annotations

from collections import Counter

from otm_core_schema import FrameworkRef
from otm_framework_mappings.ai_heuristic_registry import (
    HeuristicFrameworkRegistry,
    default_ai_heuristic_registry,
)
from otm_framework_mappings.registry import StrideFrameworkRegistry, default_stride_registry

from otm_threat_engine.result import AnalysisResult, HeuristicThreat


def _resolve_registry(registry: StrideFrameworkRegistry | None) -> StrideFrameworkRegistry:
    return registry or default_stride_registry()


def _resolve_ai_registry(registry: HeuristicFrameworkRegistry | None) -> HeuristicFrameworkRegistry:
    return registry or default_ai_heuristic_registry()


def _dedupe_refs(refs: list[FrameworkRef]) -> list[FrameworkRef]:
    seen: set[tuple[str, str]] = set()
    out: list[FrameworkRef] = []
    for r in refs:
        key = (r.framework, r.control_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


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
    ai_registry: HeuristicFrameworkRegistry,
) -> list[HeuristicThreat]:
    return [enrich_heuristic_threat(h, registry=registry, ai_registry=ai_registry) for h in heuristics]


def enrich_heuristic_threat(
    h: HeuristicThreat,
    registry: StrideFrameworkRegistry | None = None,
    ai_registry: HeuristicFrameworkRegistry | None = None,
) -> HeuristicThreat:
    reg = _resolve_registry(registry)
    ai_reg = _resolve_ai_registry(ai_registry)
    # STRIDE refs primeiro (rastreabilidade de categoria), depois refs de IA por id.
    refs = _dedupe_refs([*reg.refs_for_stride(h.stride), *ai_reg.refs_for_heuristic(h.id)])
    if not refs:  # pragma: no cover - shipped registry has refs for every StrideCategory
        return h
    return h.model_copy(update={"framework_refs": refs})


def enrich_analysis_framework_refs(
    result: AnalysisResult,
    registry: StrideFrameworkRegistry | None = None,
    ai_registry: HeuristicFrameworkRegistry | None = None,
) -> AnalysisResult:
    reg = _resolve_registry(registry)
    ai_reg = _resolve_ai_registry(ai_registry)
    new_heuristics = _enrich_heuristics_with_framework_refs(result.heuristic_threats, registry=reg, ai_registry=ai_reg)
    summary = result.summary.model_copy(
        update={"framework_ref_counts_by_catalog": _count_framework_refs(new_heuristics)}
    )
    return result.model_copy(update={"heuristic_threats": new_heuristics, "summary": summary})
