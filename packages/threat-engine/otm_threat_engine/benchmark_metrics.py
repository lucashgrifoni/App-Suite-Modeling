"""
Métricas agregadas para benchmark e CI (aproximações conservadoras).

Não substituem auditoria; servem para regressão e evolução do motor.
"""

from __future__ import annotations

from dataclasses import dataclass

from otm_core_schema import ThreatModelDocument

from otm_threat_engine.result import AnalysisResult


@dataclass(frozen=True)
class BenchmarkMetrics:
    """Métricas derivadas de um par documento + análise."""

    model_completeness_score: float
    recommendation_fit_score: float
    generic_finding_ratio: float
    specificity_ratio: float
    signal_to_noise_ratio: float
    coverage_of_expected_risks: float
    top_10_actionability_score: float
    methodology_delta: float
    anti_pattern_signal_density: float
    recommendation_relevance_score: float
    semantic_alignment_score: float


def _generic_title(h) -> bool:
    t = (h.title or "").lower()
    return any(
        x in t
        for x in (
            "tampering",
            "disclosure",
            "genérico",
            "generic",
            "canal",
        )
    )


def compute_benchmark_metrics(
    doc: ThreatModelDocument,
    analysis: AnalysisResult,
    *,
    expected_stride_prefixes: tuple[str, ...] = (),
) -> BenchmarkMetrics:
    """
    Calcula métricas heurísticas.

    `expected_stride_prefixes`: IDs ou prefixos de heurísticas esperadas para cobertura (opcional).
    """
    active = [h for h in analysis.heuristic_threats if not h.skipped_as_duplicate]
    n = max(1, len(active))
    generic_n = sum(1 for h in active if _generic_title(h))
    generic_finding_ratio = generic_n / n
    specificity_ratio = 1.0 - generic_finding_ratio

    skipped = analysis.summary.heuristic_threats_skipped_duplicate
    signal_to_noise_ratio = len(active) / max(1, len(active) + skipped)

    pq = analysis.model_quality_precheck
    mc = float(pq.score_0_100) if pq else 0.0
    fit_map = pq.methodology_fit_matrix if pq else {}
    stride_fit = fit_map.get("stride", "weak")
    rec_fit = {"strong": 1.0, "partial": 0.6, "weak": 0.3}.get(stride_fit, 0.3)
    conf_map = {"high": 1.0, "medium": 0.65, "low": 0.35}
    rec_conf = conf_map.get(pq.recommendation_confidence if pq else "low", 0.35)
    recommendation_fit_score = round(100.0 * (0.5 * rec_fit + 0.5 * rec_conf), 2)

    coverage = 0.0
    if expected_stride_prefixes and active:
        ids = " ".join(h.id for h in active)
        hits = sum(1 for p in expected_stride_prefixes if p in ids)
        coverage = hits / max(1, len(expected_stride_prefixes))

    top10 = sorted(active, key=lambda h: -(h.risk.score or 0))[:10]
    actionability = (
        sum(1 for h in top10 if not _generic_title(h)) / max(1, len(top10))
        if top10
        else 0.0
    )
    top_10_actionability_score = round(100.0 * actionability, 2)

    mc_info = analysis.methodology_completeness
    methodology_delta = (
        {"complete": 1.0, "partial": 0.5, "degraded": 0.2}.get(mc_info.state.value, 0.5)
        if mc_info
        else 0.5
    )

    ap_n = len(analysis.anti_pattern_hits)
    anti_pattern_signal_density = round(min(1.0, ap_n / 8.0), 4)

    recommendation_relevance_score = round(
        0.5 * recommendation_fit_score + 0.5 * (100.0 * (1.0 - generic_finding_ratio)),
        2,
    )

    semantic_alignment_score = round(100.0 * (1.0 - generic_finding_ratio), 2)

    return BenchmarkMetrics(
        model_completeness_score=mc,
        recommendation_fit_score=recommendation_fit_score,
        generic_finding_ratio=round(generic_finding_ratio, 4),
        specificity_ratio=round(specificity_ratio, 4),
        signal_to_noise_ratio=round(signal_to_noise_ratio, 4),
        coverage_of_expected_risks=round(coverage, 4),
        top_10_actionability_score=top_10_actionability_score,
        methodology_delta=methodology_delta,
        anti_pattern_signal_density=anti_pattern_signal_density,
        recommendation_relevance_score=recommendation_relevance_score,
        semantic_alignment_score=semantic_alignment_score,
    )
