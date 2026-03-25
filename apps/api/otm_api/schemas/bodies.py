from __future__ import annotations

from typing import Any, Literal

from otm_core_schema import ThreatModelMethodology
from otm_explainability import ExplanationRecord
from pydantic import BaseModel, Field, model_validator

from otm_api.domain.export_formats import ExportFormat


class DocumentBody(BaseModel):
    """Corpo com documento canónico serializado como objeto JSON."""

    document: dict[str, Any] = Field(
        ...,
        description="Raiz compatível com `ThreatModelDocument` (aliases YAML respeitados).",
    )


class DiffBody(BaseModel):
    """Duas raízes `ThreatModelDocument` para comparação estruturada (sem persistência)."""

    baseline: dict[str, Any] = Field(
        ...,
        description="Versão anterior (baseline) — mesmo formato que `document` em /validate.",
    )
    revised: dict[str, Any] = Field(..., description="Versão nova (revisão).")


class CompareBody(BaseModel):
    """
    Comparação completa: estrutura + opcional análise (payload explícito ou `run_analysis`).
    """

    baseline: dict[str, Any] = Field(..., description="Documento canónico baseline.")
    revised: dict[str, Any] = Field(..., description="Documento canónico revisão.")
    baseline_analysis: dict[str, Any] | None = Field(
        default=None,
        description="Resultado de `analyze` em JSON (opcional).",
    )
    revised_analysis: dict[str, Any] | None = Field(default=None, description="Análise da revisão (opcional).")
    run_analysis: bool = Field(
        default=False,
        description="Se true e análises não forem enviadas, executa o motor em ambos os documentos.",
    )
    pack_id: str | None = Field(default=None, description="Pack opcional quando `run_analysis` é true.")

    @model_validator(mode="after")
    def _pair_analyses(self) -> CompareBody:
        a, b = self.baseline_analysis, self.revised_analysis
        if (a is None) != (b is None):
            raise ValueError("Forneça ambos baseline_analysis e revised_analysis, ou nenhum.")
        return self


class AnalysisDiffBody(BaseModel):
    """Dois `AnalysisResult` serializados (ex.: ficheiros gerados por `otm analyze --json-out`)."""

    baseline_analysis: dict[str, Any]
    revised_analysis: dict[str, Any]


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
        description=(
            "Metodologia/engine explícita. Se ausente, usa `document.model.methodology` "
            "(default STRIDE)."
        ),
    )
    auto_recommend_methodology: bool = Field(
        default=False,
        description="Se true e `methodology` não informado, aplica recomendação automática.",
    )


class RecommendMethodologyResponse(BaseModel):
    methodology: ThreatModelMethodology
    reason: str
    explanations: list[ExplanationRecord] = Field(default_factory=list)


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


class InferenceRecordBody(BaseModel):
    """Uma inferência assistida (transparência obrigatória)."""

    id: str
    message: str
    confidence: Literal["low", "medium", "high"]
    source: Literal["openapi", "terraform", "kubernetes", "helm"]
    related_component_ids: list[str] = Field(default_factory=list)


class RemediationBacklogRequest(BaseModel):
    """Entrada para gerar backlog: sempre `document`; `analysis` opcional se `run_analysis`."""

    document: dict[str, Any] = Field(..., description="Raiz `ThreatModelDocument`.")
    analysis: dict[str, Any] | None = Field(
        default=None,
        description="Resultado de `analyze` (JSON). Obrigatório se `run_analysis` é false.",
    )
    run_analysis: bool = Field(
        default=False,
        description="Se true, executa o motor quando `analysis` está ausente.",
    )
    pack_id: str | None = Field(default=None, description="Pack para `run_analysis`.")
    methodology: ThreatModelMethodology | None = Field(default=None)
    auto_recommend_methodology: bool = Field(default=False)


class ArtifactImportResponse(BaseModel):
    """Rascunho canónico + lista estruturada de inferências (não é `AnalysisResult`)."""

    document: dict[str, Any]
    inferences: list[InferenceRecordBody]
    unknowns: list[str]
    assumptions: list[str]
    explanations: list[ExplanationRecord] = Field(default_factory=list)
