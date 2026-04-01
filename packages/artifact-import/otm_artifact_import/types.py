"""Tipos partilhados para importação assistida de artefactos."""

from __future__ import annotations

from typing import Literal

from otm_core_schema import ThreatModelDocument
from otm_explainability import ExplanationRecord
from pydantic import BaseModel, Field

ConfidenceLevel = Literal["low", "medium", "high"]


class InferenceRecord(BaseModel):
    """Explicabilidade: cada inferência relevante é explícita e audível."""

    id: str = Field(..., description="Identificador estável dentro do lote de importação.")
    message: str = Field(..., description="Texto humano: o que foi inferido e a partir de quê.")
    confidence: ConfidenceLevel = Field(
        default="medium",
        description="high = derivado directamente do artefacto; medium/low = heurística ou parcial.",
    )
    source: Literal["openapi", "terraform", "kubernetes", "helm"] = Field(
        ..., description="Tipo de artefacto analisado."
    )
    related_component_ids: list[str] = Field(
        default_factory=list,
        description="IDs de componentes afectados, se aplicável.",
    )


class ArtifactImportResult(BaseModel):
    """Resultado de uma importação assistida — draft canónico + transparência."""

    document: ThreatModelDocument
    inferences: list[InferenceRecord] = Field(default_factory=list)
    explanations: list[ExplanationRecord] = Field(
        default_factory=list,
        description="Mesmas inferências no contrato de explicabilidade (API/relatórios).",
    )
    unknowns: list[str] = Field(
        default_factory=list,
        description="O que não foi possível inferir com segurança.",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Premissas documentadas (também espelhadas em business_context quando cabe).",
    )
