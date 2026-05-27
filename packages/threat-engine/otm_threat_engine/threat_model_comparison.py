"""
Orquestra diff estrutural (`otm_core_schema`) + diff de análise (`analysis_diff`).

Único ponto de entrada recomendado para CLI/API quando se quer visão unificada.
"""

from __future__ import annotations

from otm_core_schema.diff import ThreatModelDiff, diff_documents
from otm_core_schema.diff_insights import structural_key_insights
from otm_core_schema.document import ThreatModelDocument

from otm_threat_engine.analysis_diff import diff_analysis_results
from otm_threat_engine.comparison_explanations import build_comparison_explanations
from otm_threat_engine.comparison_models import (
    AnalysisDiff,
    ComparisonResultMeta,
    ComparisonSummary,
    DiffAggregate,
    HeuristicThreatDeltaSection,
    RecommendationDelta,
    RiskDeltaSummary,
    ThreatDeltaSummary,
    ThreatModelComparisonResult,
)
from otm_threat_engine.result import AnalysisResult
from otm_threat_engine.semantic_comparison import enrich_comparison_meta


def _agg_from_structural(d: ThreatModelDiff) -> DiffAggregate:
    return DiffAggregate(
        components={
            "added": d.components.added,
            "removed": d.components.removed,
            "changed": [m.id for m in d.components.modified],
        },
        assets={
            "added": d.assets.added,
            "removed": d.assets.removed,
            "changed": [m.id for m in d.assets.modified],
        },
        data_flows={
            "added": d.data_flows.added,
            "removed": d.data_flows.removed,
            "changed": [m.id for m in d.data_flows.modified],
        },
        trust_boundaries={
            "added": d.trust_boundaries.added,
            "removed": d.trust_boundaries.removed,
            "changed": [m.id for m in d.trust_boundaries.modified],
        },
        threats={
            "added": d.threats.added,
            "removed": d.threats.removed,
            "changed": [m.id for m in d.threats.modified],
        },
        mitigations={
            "added": d.mitigations.added,
            "removed": d.mitigations.removed,
            "changed": [m.id for m in d.mitigations.modified],
        },
        evidence_suggestions={
            "added": d.evidence_suggestions.added,
            "removed": d.evidence_suggestions.removed,
            "changed": [m.id for m in d.evidence_suggestions.modified],
        },
    )


def _analysis_has_changes(ad: AnalysisDiff) -> bool:
    ht = ad.heuristic_threats
    mi = ad.methodology_insights
    tb = ad.trust_boundary_findings
    sf = ad.structural_findings
    return any(
        (
            ad.methodology_changed,
            ad.signature_remap_hints,
            ht.added,
            ht.removed,
            ht.modified,
            ad.framework_ref_counts,
            ad.pack_control_hints.added,
            ad.pack_control_hints.removed,
            bool(mi and (mi.blocks_added or mi.blocks_removed or mi.profile_before != mi.profile_after)),
            bool(tb and (tb.added_keys or tb.removed_keys)),
            bool(sf and (sf.codes_added or sf.codes_removed)),
            (ad.max_risk_delta or 0) != 0,
        )
    )


def _heuristic_change_insights(ad: AnalysisDiff) -> list[str]:
    out: list[str] = []
    for h in ad.heuristic_threats.added[:10]:
        score_note = f" (score {h.score_after})" if h.score_after is not None else ""
        out.append(f"Heurística nova ativa: `{h.threat_id}`{score_note}.")
    for h in ad.heuristic_threats.removed[:10]:
        out.append(
            f"Heurística ativa deixou de existir: `{h.threat_id}`"
            + (f" (era score {h.score_before})" if h.score_before is not None else "")
            + "."
        )
    for h in ad.heuristic_threats.modified:
        if h.score_delta is not None and h.score_delta > 0:
            out.append(f"Risco da heurística `{h.threat_id}` subiu (Δ score {h.score_delta:+.1f}).")
        elif h.score_delta is not None and h.score_delta < 0:
            out.append(f"Risco da heurística `{h.threat_id}` desceu (Δ score {h.score_delta:+.1f}).")
    return out


def _framework_pack_insights(ad: AnalysisDiff) -> list[str]:
    out: list[str] = []
    for fr in ad.framework_ref_counts:
        if fr.count_after < fr.count_before:
            out.append(
                f"Menos referências mapeadas em `{fr.catalog}` ({fr.count_before} → {fr.count_after}); "
                "cobertura de controlos pode ter regressado."
            )
        elif fr.count_after > fr.count_before:
            out.append(f"Mais referências em `{fr.catalog}` ({fr.count_before} → {fr.count_after}).")
    if ad.pack_control_hints.removed:
        out.append(
            "Controlo(s) do pack deixaram de ser sugeridos: "
            + "; ".join(ad.pack_control_hints.removed[:5])
            + ("…" if len(ad.pack_control_hints.removed) > 5 else "")
        )
    if ad.pack_control_hints.added:
        joined = "; ".join(ad.pack_control_hints.added[:5])
        suffix = "…" if len(ad.pack_control_hints.added) > 5 else ""
        out.append("Novas sugestões de controlo do pack: " + joined + suffix)
    return out


def _analysis_insights(ad: AnalysisDiff) -> list[str]:
    insights: list[str] = []
    if ad.methodology_changed:
        insights.append(
            f"Análise executada com metodologia diferente: {ad.methodology_before} → {ad.methodology_after}."
        )
    if ad.max_risk_delta is not None and ad.max_risk_delta != 0:
        insights.append(
            f"Score máximo entre ameaças ativas mudou: {ad.max_risk_before} → {ad.max_risk_after} "
            f"(Δ {ad.max_risk_delta:+.1f})."
        )
    insights.extend(_heuristic_change_insights(ad))
    insights.extend(ad.signature_remap_hints[:10])
    insights.extend(_framework_pack_insights(ad))
    tb = ad.trust_boundary_findings
    if tb and (tb.added_keys or tb.removed_keys):
        insights.append(
            f"Achados de cruzamento de fronteira: +{len(tb.added_keys)} novo(s), "
            f"−{len(tb.removed_keys)} deixaram de aparecer."
        )
    seen: set[str] = set()
    out: list[str] = []
    for s in insights:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _merge_key_insights(a: list[str], b: list[str], *, max_items: int = 32) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for block in (a, b):
        for s in block:
            if s not in seen:
                seen.add(s)
                out.append(s)
            if len(out) >= max_items:
                return out
    return out


def _build_risk_delta(analysis: AnalysisDiff | None, *, residual_changed: bool) -> RiskDeltaSummary:
    mods = analysis.heuristic_threats.modified if analysis else []
    added = analysis.heuristic_threats.added if analysis else []
    removed = analysis.heuristic_threats.removed if analysis else []
    return RiskDeltaSummary(
        analysis_max_score_baseline=analysis.max_risk_before if analysis else None,
        analysis_max_score_revised=analysis.max_risk_after if analysis else None,
        analysis_max_score_delta=analysis.max_risk_delta if analysis else None,
        heuristic_increased_ids=[h.threat_id for h in mods if (h.score_delta or 0) > 0]
        + [h.threat_id for h in added],
        heuristic_decreased_ids=[h.threat_id for h in mods if (h.score_delta or 0) < 0]
        + [h.threat_id for h in removed],
        document_residual_aggregate_changed=residual_changed,
    )


def _build_recommendation_delta(analysis: AnalysisDiff | None) -> RecommendationDelta:
    if analysis is None:
        return RecommendationDelta()
    mi = analysis.methodology_insights
    return RecommendationDelta(
        pack_hints_added=analysis.pack_control_hints.added,
        pack_hints_removed=analysis.pack_control_hints.removed,
        framework_catalog_deltas=list(analysis.framework_ref_counts),
        methodology_insight_blocks_added=list(mi.blocks_added if mi else []),
        methodology_insight_blocks_removed=list(mi.blocks_removed if mi else []),
    )


def compare_threat_models(
    baseline: ThreatModelDocument,
    revised: ThreatModelDocument,
    *,
    baseline_analysis: AnalysisResult | None = None,
    revised_analysis: AnalysisResult | None = None,
) -> ThreatModelComparisonResult:
    """
    Compara dois modelos; se ambas as análises forem fornecidas, inclui diff de risco/heurísticas.

    Matching: documento sempre por **id**. Heurísticas por **id**, com hints de assinatura em
    `analysis.signature_remap_hints`.
    """
    structural = diff_documents(baseline, revised)
    aggregate = _agg_from_structural(structural)
    s_insights = structural_key_insights(baseline, revised, structural)

    analysis: AnalysisDiff | None = None
    a_insights: list[str] = []
    if baseline_analysis is not None and revised_analysis is not None:
        analysis = diff_analysis_results(baseline_analysis, revised_analysis)
        a_insights = _analysis_insights(analysis)

    meth_model_changed = any(c.field == "methodology" for c in structural.model_info)
    has_a = analysis is not None and _analysis_has_changes(analysis)

    headline = structural.summary_line
    if analysis:
        headline += f" | análise: metodologia {analysis.methodology_before}→{analysis.methodology_after}, "
        headline += f"Δscore_max={analysis.max_risk_delta!s}"

    risk_delta = _build_risk_delta(analysis, residual_changed=bool(structural.residual_risk_summary))

    heuristic_section = analysis.heuristic_threats if analysis else HeuristicThreatDeltaSection()

    threat_delta = ThreatDeltaSummary(
        canonical=structural.threats,
        heuristic=heuristic_section,
    )

    rec = _build_recommendation_delta(analysis)

    key_insights = _merge_key_insights(s_insights, a_insights)

    summary = ComparisonSummary(
        headline=headline[:500],
        has_structural_changes=structural.has_any_change(),
        has_analysis_changes=has_a,
        methodology_in_model_changed=meth_model_changed,
    )

    meta = ComparisonResultMeta.model_validate(
        {
            "comparison_contract_version": "1.5",
            **enrich_comparison_meta(
                baseline,
                revised,
                baseline_analysis=baseline_analysis,
                revised_analysis=revised_analysis,
                aggregate=aggregate,
            ),
        }
    )
    # Inclui insights semânticos (estrutura + análise) na lista principal para CLI/Markdown legível.
    sem_list = list(meta.semantic_insights or [])
    seen_ki: set[str] = set(key_insights)
    for s in sem_list:
        if s not in seen_ki and len(key_insights) < 48:
            seen_ki.add(s)
            key_insights.append(s)

    base = ThreatModelComparisonResult(
        summary=summary,
        aggregate=aggregate,
        structural=structural,
        structural_insights=s_insights,
        analysis=analysis,
        analysis_insights=a_insights,
        risk_delta=risk_delta,
        threat_delta=threat_delta,
        recommendation_delta=rec,
        key_insights=key_insights,
        meta=meta,
    )
    return base.model_copy(update={"explanations": build_comparison_explanations(base)})
