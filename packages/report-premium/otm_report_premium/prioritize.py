"""Priorização composta P1/P2/P3 — combina severidade, exploitability e remediação."""

from __future__ import annotations

from typing import Literal

from otm_core_schema import StrideCategory, ThreatModelMethodology
from otm_core_schema.document import ThreatModelDocument
from otm_threat_engine.remediation.classify import classify_threat, effort_for_threat
from otm_threat_engine.result import HeuristicThreat

from .risk_context import infer_exploitability


def _risk_score(t: HeuristicThreat) -> float:
    if t.risk.score is not None:
        return float(t.risk.score)
    return float(t.risk.likelihood * t.risk.impact)


def _effort_weight(effort: str) -> float:
    return {"low": 0.2, "medium": 0.5, "high": 0.9}.get(effort, 0.5)


def _exploit_weight(exp: float) -> float:
    """Peso 0–1: maior = mais facilmente explorável no modelo heurístico."""
    return min(1.0, max(0.0, exp))


def composite_priority_score(
    threat: HeuristicThreat,
    doc: ThreatModelDocument | None,
    methodology: ThreatModelMethodology,
) -> float:
    """
    Score contínuo para ordenação; não é CVSS.
    """
    rs = _risk_score(threat)
    root, _ctrl, _cat, _layer = classify_threat(threat, doc, methodology)
    effort = effort_for_threat(threat, root)
    ew = _exploit_weight(rs / 25.0)

    ex = infer_exploitability(threat, doc)
    remote_boost = 0.15 if ex.attack_locality in ("remote", "hybrid") else 0.0
    edge_boost = 0.1 if ex.requires_external_access else 0.0

    # Normaliza risco ~0–25 para 0–1
    r_norm = min(1.0, rs / 25.0)
    high_stride = (
        StrideCategory.INFORMATION_DISCLOSURE,
        StrideCategory.ELEVATION_OF_PRIVILEGE,
    )
    biz = 0.55 if threat.stride in high_stride else 0.4
    remed_inv = 1.0 - _effort_weight(effort)

    score = 0.35 * r_norm + 0.22 * ew + 0.18 * biz + 0.15 * remed_inv + 0.07 * (remote_boost + edge_boost)
    return round(score, 4)


def assign_priority_tier(rank_index: int, total: int) -> Literal["P1", "P2", "P3"]:
    """Tercis: P1 topo ~33%, P2 meio, P3 resto."""
    if total <= 0:
        return "P3"
    third = max(1, total // 3)
    if rank_index < third:
        return "P1"
    if rank_index < 2 * third:
        return "P2"
    return "P3"


def horizon_for_tier(tier: Literal["P1", "P2", "P3"]) -> Literal["immediate", "short", "medium"]:
    if tier == "P1":
        return "immediate"
    if tier == "P2":
        return "short"
    return "medium"
