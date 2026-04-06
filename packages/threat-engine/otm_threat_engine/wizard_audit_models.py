"""
Entradas de audit trail para influência do assistente (`wz:` tags).

Mantidas num módulo pequeno para evitar importações circulares com `result` / `anti_pattern_library`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class WizardSignalTraceEntry(BaseModel):
    """Uma linha auditável: o que foi declarado, efeito e onde se reflecte."""

    source_tag: str = Field(..., description="Tag original, ex.: wz:profile:key=no")
    effect: Literal["ranking_impact", "corpus_mitigation", "observation"] = Field(
        ...,
        description=(
            "ranking_impact: reforço L×I; corpus_mitigation: keywords no anti-pattern; "
            "observation: só rastreio."
        ),
    )
    weight: Literal["low", "moderate"] = "low"
    impact_areas: list[str] = Field(
        default_factory=list,
        description="Ex.: heuristic_ranking, anti_pattern_corpus.",
    )
    mechanism: Literal["direct", "contextual", "auxiliary"] = "contextual"
    explanation: str = Field(..., description="Texto curto para humanos / governança.")
