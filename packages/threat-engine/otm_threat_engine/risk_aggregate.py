"""Consolidação executiva de risco a partir de heurísticas (pós-lente)."""

from __future__ import annotations

from collections import Counter
from typing import Any, Literal

from pydantic import BaseModel, Field

from otm_threat_engine.result import AnalysisResult, HeuristicThreat


def _active(h: HeuristicThreat) -> bool:
    return not h.skipped_as_duplicate


def _severity_bucket(score: float) -> str:
    if score >= 20:
        return "critical"
    if score >= 12:
        return "high"
    if score >= 6:
        return "medium"
    return "low"


class AggregateRiskSummary(BaseModel):
    schema_version: str = "1.0"
    active_threat_count: int = 0
    total_risk_score: float = 0.0
    mean_risk_score: float | None = None
    max_risk_score: float | None = None
    severity_distribution: dict[str, int] = Field(default_factory=dict)
    top_threats: list[dict[str, Any]] = Field(default_factory=list)
    top_components: list[dict[str, Any]] = Field(default_factory=list)
    top_flows: list[dict[str, Any]] = Field(default_factory=list)
    top_assets: list[dict[str, Any]] = Field(default_factory=list)
    dominant_themes: list[str] = Field(default_factory=list)
    mitigation_starters: list[str] = Field(default_factory=list)


class DecisionCockpitSummary(BaseModel):
    schema_version: str = "1.0"
    risk_posture: Literal["low", "moderate", "high", "elevated"] = "moderate"
    headline: str = ""
    key_decisions: list[str] = Field(default_factory=list)
    next_reviews: list[str] = Field(default_factory=list)


def build_aggregate_and_cockpit(result: AnalysisResult) -> dict[str, AggregateRiskSummary | DecisionCockpitSummary]:
    active = [h for h in result.heuristic_threats if _active(h)]
    scores = [float(h.risk.score) for h in active if h.risk.score is not None]
    total = float(sum(scores)) if scores else 0.0
    mean = (total / len(scores)) if scores else None
    mx = max(scores) if scores else None
    sev = Counter(_severity_bucket(s) for s in scores)
    top_threats_sorted = sorted(active, key=lambda h: -(float(h.risk.score) if h.risk.score is not None else 0.0))[:8]
    top_threat_payload = [
        {
            "id": h.id,
            "title": h.title,
            "score": float(h.risk.score) if h.risk.score is not None else None,
            "stride": h.stride.value,
        }
        for h in top_threats_sorted
    ]

    by_comp: dict[str, float] = {}
    by_flow: dict[str, float] = {}
    by_asset: dict[str, float] = {}
    families: Counter[str] = Counter()
    for h in active:
        sc = float(h.risk.score) if h.risk.score is not None else 0.0
        if h.target_component_id:
            by_comp[h.target_component_id] = by_comp.get(h.target_component_id, 0) + sc
        if h.target_data_flow_id:
            by_flow[h.target_data_flow_id] = by_flow.get(h.target_data_flow_id, 0) + sc
        if h.target_asset_id:
            by_asset[h.target_asset_id] = by_asset.get(h.target_asset_id, 0) + sc
        if h.finding_family:
            families[h.finding_family] += 1
        prefix = (h.id.split("_", 1)[0] if h.id else "") or ""
        if prefix:
            families[prefix] += 1

    def _top(score_map: dict[str, float], n: int = 5) -> list[dict[str, Any]]:
        return [{"id": k, "aggregate_score": round(v, 2)} for k, v in sorted(score_map.items(), key=lambda x: -x[1])[:n]]

    themes = [f"{k}: {v}" for k, v in families.most_common(8)]
    mitigations: list[str] = []
    for h in top_threats_sorted[:5]:
        tgt = h.target_component_id or h.target_data_flow_id or h.target_asset_id or "alvo"
        mitigations.append(f"Priorizar `{h.id}` em `{tgt}` (score {h.risk.score}).")

    agg = AggregateRiskSummary(
        active_threat_count=len(active),
        total_risk_score=round(total, 2),
        mean_risk_score=round(mean, 2) if mean is not None else None,
        max_risk_score=round(mx, 2) if mx is not None else None,
        severity_distribution=dict(sev),
        top_threats=top_threat_payload,
        top_components=_top(by_comp),
        top_flows=_top(by_flow),
        top_assets=_top(by_asset),
        dominant_themes=themes,
        mitigation_starters=mitigations[:12],
    )

    if mx is None or mx < 6:
        posture: Literal["low", "moderate", "high", "elevated"] = "low"
        headline = "Postura agregada baixa com as heurísticas actuais (rever cobertura do modelo)."
    elif mx < 12:
        posture = "moderate"
        headline = "Postura moderada: priorizar superfícies nos top rankings."
    elif mx < 20:
        posture = "high"
        headline = "Postura elevada — concentrar mitigação nos maiores scores."
    else:
        posture = "elevated"
        headline = "Postura crítica agregada — tratamento prioritário recomendado."

    cockpit = DecisionCockpitSummary(
        risk_posture=posture,
        headline=headline,
        key_decisions=[
            f"{len(active)} achados heurísticos activos; soma de scores ≈ {total:.1f}.",
            "Ordenar backlog pelos `top_threats` e validar com donos de sistema.",
        ],
        next_reviews=[
            "Rever controlos nas fronteiras com fluxos de maior risco acumulado.",
            "Confirmar classificação e retenção nos ativos mais expostos.",
        ],
    )
    return {"aggregate_risk": agg, "decision_cockpit": cockpit}
