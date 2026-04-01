"""Contratos declarativos para industry packs (YAML)."""

from __future__ import annotations

from typing import Literal

from otm_core_schema.enums import ComponentKind, IndustrySector, StrideCategory
from pydantic import BaseModel, Field


class RiskTuning(BaseModel):
    """Ajusta L×I do motor base (multiplicadores suaves, 0.5–2.0)."""

    likelihood_multiplier: float = Field(default=1.0, ge=0.5, le=2.0)
    impact_multiplier: float = Field(default=1.0, ge=0.5, le=2.0)


class AdditionalThreatRule(BaseModel):
    """Ameaça extra sugerida pelo setor (uma instância por componente compatível)."""

    id: str = Field(..., pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$")
    title: str = Field(..., min_length=1)
    description: str | None = None
    stride: StrideCategory
    target_component_kinds: list[ComponentKind] = Field(
        default_factory=list,
        description="Vazio = aplica a qualquer componente.",
    )
    likelihood_delta: int = Field(default=0, ge=-2, le=2)
    impact_delta: int = Field(default=0, ge=-2, le=2)


class PackDefinition(BaseModel):
    """Pack por setor — influencia risco e acrescenta ameaças de contexto."""

    id: str = Field(..., pattern=r"^[a-zA-Z][a-zA-Z0-9_-]*$")
    name: str
    sector: IndustrySector
    description: str | None = None
    risk_tuning: RiskTuning | None = None
    additional_threats: list[AdditionalThreatRule] = Field(default_factory=list)
    control_hints: list[str] = Field(
        default_factory=list,
        description="Lembretes de controlo para relatório / backlog (texto livre).",
    )


class TemplateInfo(BaseModel):
    """Metadados opcionais do template (ficheiro template manifest)."""

    id: str
    title: str
    description: str = ""
    suggested_pack: str | None = Field(
        default=None,
        description="ID do pack sugerido em analyze (opcional).",
    )
    # Catálogo (UI/API/CLI) — chave estável + etiqueta para apresentação
    category: str = Field(
        default="applications",
        description=(
            "Chave de agrupamento: applications, cloud_infra, identity_access, "
            "integrations, ai_llm, industry, objective."
        ),
    )
    category_label: str = Field(
        default="Aplicações",
        description="Rótulo curto para listagens (ex.: PT).",
    )
    tags: list[str] = Field(default_factory=list)
    complexity: Literal["low", "medium", "high"] | None = Field(
        default=None,
        description="Complexidade sugerida do modelo inicial.",
    )
    best_for: str | None = Field(
        default=None,
        description="Uma linha: cenário ideal para este template.",
    )
    suggested_methodology: str | None = Field(
        default=None,
        description="Metodologia sugerida (stride, plot4ai, linddun, …) alinhada ao draft.",
    )
    recommendation_hints: list[str] = Field(
        default_factory=list,
        description="Sinais curtos para recomendação futura (sem lógica na UI).",
    )
