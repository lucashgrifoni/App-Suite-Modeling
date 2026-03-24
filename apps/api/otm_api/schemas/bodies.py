from __future__ import annotations

from typing import Any, Literal

from otm_core_schema import ThreatModelMethodology
from pydantic import BaseModel, Field

from otm_api.domain.export_formats import ExportFormat


class DocumentBody(BaseModel):
    """Corpo com documento canónico serializado como objeto JSON."""

    document: dict[str, Any] = Field(
        ...,
        description="Raiz compatível com `ThreatModelDocument` (aliases YAML respeitados).",
    )


class ValidateResponse(BaseModel):
    valid: Literal[True] = True
    title: str = Field(..., description="Título em `metadata.title`.")
    schema_version: str = Field(..., description="Versão do schema canónico.")
    component_count: int = 0
    threat_count: int = 0


class CreateModelResponse(BaseModel):
    document: dict[str, Any] = Field(..., description="Modelo mínimo novo, pronto a editar.")


class AnalyzeBody(DocumentBody):
    pack_id: str | None = Field(
        default=None,
        description="Industry pack opcional (mesmos IDs que `otm analyze --pack`).",
    )
    methodology: ThreatModelMethodology | None = Field(
        default=None,
        description="Metodologia/engine explícita. Se ausente, usa `document.model.methodology` (default STRIDE).",
    )
    auto_recommend_methodology: bool = Field(
        default=False,
        description="Se true e `methodology` não informado, aplica recomendação automática.",
    )


class RecommendMethodologyResponse(BaseModel):
    methodology: ThreatModelMethodology
    reason: str


class ExportBody(DocumentBody):
    formats: list[ExportFormat] = Field(
        default_factory=lambda: [ExportFormat.document_json],
        description="Um ou mais formatos de saída.",
    )
    pack_id: str | None = Field(
        default=None,
        description="Usado se for preciso correr análise para formatos que a exigem.",
    )
    analysis: dict[str, Any] | None = Field(
        default=None,
        description="Resultado de análise já calculado (opcional); evita reexecutar o motor.",
    )


class ExportResponse(BaseModel):
    artifacts: dict[str, str] = Field(
        ...,
        description="Chave = id do formato; valor = texto (JSON, Markdown ou Mermaid).",
    )
