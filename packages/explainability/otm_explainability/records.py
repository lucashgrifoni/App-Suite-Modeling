"""
Contrato partilhado de explicabilidade — curto, contextualizado, sem black box.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field

ConfidenceLevel = Literal["low", "medium", "high"]


class ExplanationType(StrEnum):
    """Natureza do raciocínio (para filtros e relatórios)."""

    METHODOLOGY_RECOMMENDATION = "methodology_recommendation"
    THREAT_HEURISTIC = "threat_heuristic"
    RISK_SCORE = "risk_score"
    CONTROL_SUGGESTION = "control_suggestion"
    BACKLOG_PRIORITIZATION = "backlog_prioritization"
    IMPORT_INFERENCE = "import_inference"
    TRUST_BOUNDARY = "trust_boundary"
    STRUCTURAL_FINDING = "structural_finding"
    DIFF_CHANGE = "diff_change"
    AGGREGATION = "aggregation"
    AI_SPECIALIZED_RATIONALE = "ai_specialized_rationale"


class ExplanationCategory(StrEnum):
    """Área funcional (alinhada aos motores do produto)."""

    METHODOLOGY = "methodology"
    THREAT = "threat"
    RISK = "risk"
    CONTROL = "control"
    BACKLOG = "backlog"
    IMPORT = "import"
    TRUST_BOUNDARY = "trust_boundary"
    DIFF = "diff"
    GOVERNANCE = "governance"
    AI_MODELING = "ai_modeling"


class RelatedEntityRef(BaseModel):
    """Ligação a uma entidade do modelo ou do resultado de motor."""

    entity_kind: str = Field(
        ...,
        description="ex.: heuristic_threat, component, data_flow, trust_boundary, document",
    )
    entity_id: str


class ExplanationRecord(BaseModel):
    """
    Explicação única e auditável.

    `message` deve ser específica ao contexto; `evidence` lista factos discretos que a suportam.
    """

    id: str
    type: ExplanationType
    category: ExplanationCategory
    subject: str = Field(..., max_length=200, description="O que está a ser explicado (curto).")
    message: str = Field(..., description="Porquê, em linguagem directa para humanos.")
    evidence: list[str] = Field(
        default_factory=list,
        description="Factos do modelo/artefacto que sustentam a mensagem.",
    )
    confidence: ConfidenceLevel = Field(
        default="medium",
        description="high = regra directa sobre dados explícitos; low = heurística fraca.",
    )
    related_entities: list[RelatedEntityRef] = Field(default_factory=list)
    reasoning_path: list[str] | None = Field(
        default=None,
        description="Passos opcionais do raciocínio (maiores que 1 decisão).",
    )
