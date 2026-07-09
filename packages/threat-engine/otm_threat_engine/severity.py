"""Banda de severidade canónica a partir do score L×I (1–25).

Fonte única de verdade. O score é `likelihood × impact` (1–5 cada), e a banda
alimenta `AggregateRiskSummary.severity_distribution`, os relatórios e os gates
de CI. Qualquer superfície que rotule severidade deve usar `severity_for_score`
em vez de recriar os limiares — divergências fazem a mesma ameaça aparecer como
`high` num sítio e `medium` noutro.
"""

from __future__ import annotations

from typing import Final, Literal

Severity = Literal["low", "medium", "high", "critical"]

#: Ordem crescente de gravidade — índice usado para comparações de limiar.
SEVERITY_ORDER: Final[tuple[Severity, ...]] = ("low", "medium", "high", "critical")

_CRITICAL_MIN: Final = 20.0
_HIGH_MIN: Final = 12.0
_MEDIUM_MIN: Final = 6.0


def severity_for_score(score: float | None) -> Severity:
    """Mapeia um score L×I (1–25) para a banda canónica. `None` conta como `low`."""
    s = score or 0.0
    if s >= _CRITICAL_MIN:
        return "critical"
    if s >= _HIGH_MIN:
        return "high"
    if s >= _MEDIUM_MIN:
        return "medium"
    return "low"


def severity_rank(severity: Severity) -> int:
    """Índice em `SEVERITY_ORDER` (low=0 … critical=3)."""
    return SEVERITY_ORDER.index(severity)


def severity_at_least(severity: Severity, threshold: Severity) -> bool:
    """`True` quando `severity` é igual ou mais grave que `threshold`."""
    return severity_rank(severity) >= severity_rank(threshold)
