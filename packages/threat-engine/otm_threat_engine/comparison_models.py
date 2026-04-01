"""Tipos Pydantic para comparação modelo + análise (consumíveis por API/CLI/export)."""

from __future__ import annotations

from typing import Any, Literal

from otm_core_schema.diff import FieldChange, IdListSectionDiff, ThreatModelDiff
from otm_explainability import ExplanationRecord
from pydantic import BaseModel, Field


class DiffAggregate(BaseModel):
    """Vista agregada added/removed/changed por secção estrutural (IDs)."""

    components: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Chaves: added, removed, changed.",
    )
    assets: dict[str, list[str]] = Field(default_factory=dict)
    data_flows: dict[str, list[str]] = Field(default_factory=dict)
    trust_boundaries: dict[str, list[str]] = Field(default_factory=dict)
    threats: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Ameaças canónicas no documento (não heurísticas do motor).",
    )
    mitigations: dict[str, list[str]] = Field(default_factory=dict)
    evidence_suggestions: dict[str, list[str]] = Field(default_factory=dict)


class ComparisonSummary(BaseModel):
    headline: str
    has_structural_changes: bool
    has_analysis_changes: bool
    methodology_in_model_changed: bool


class HeuristicThreatDelta(BaseModel):
    threat_id: str
    change: Literal["added", "removed", "modified"]
    match_kind: Literal["id", "signature_remap"] = "id"
    score_before: float | None = None
    score_after: float | None = None
    score_delta: float | None = None
    field_changes: list[FieldChange] = Field(default_factory=list)
    paired_id: str | None = Field(
        default=None,
        description="Se match_kind=signature_remap, o ID correspondente no outro lado.",
    )


class HeuristicThreatDeltaSection(BaseModel):
    """Diff de heurísticas ativas (skipped_as_duplicate=False)."""

    added: list[HeuristicThreatDelta] = Field(default_factory=list)
    removed: list[HeuristicThreatDelta] = Field(default_factory=list)
    modified: list[HeuristicThreatDelta] = Field(default_factory=list)


class FrameworkRefCountDelta(BaseModel):
    catalog: str
    count_before: int
    count_after: int


class PackHintsDelta(BaseModel):
    added: list[str] = Field(default_factory=list)
    removed: list[str] = Field(default_factory=list)


class MethodologyInsightsDelta(BaseModel):
    profile_before: str | None = None
    profile_after: str | None = None
    blocks_added: list[str] = Field(default_factory=list)
    blocks_removed: list[str] = Field(default_factory=list)


class TrustBoundaryFindingDelta(BaseModel):
    """Contagem e chaves estáveis (code + data_flow_id)."""

    added_keys: list[str] = Field(default_factory=list)
    removed_keys: list[str] = Field(default_factory=list)
    count_before: int = 0
    count_after: int = 0


class StructuralFindingDelta(BaseModel):
    codes_added: list[str] = Field(default_factory=list)
    codes_removed: list[str] = Field(default_factory=list)
    count_before: int = 0
    count_after: int = 0


class AnalysisDiff(BaseModel):
    """
    Diff entre dois `AnalysisResult` (mesmo contrato que `analyze.json`).

    Matching de heurísticas: primário por `id`; fallback por assinatura semântica
    (stride + alvos + prefixo do título) só para *insights* de possível remapeamento.
    """

    methodology_before: str
    methodology_after: str
    methodology_changed: bool
    max_risk_before: float | None = None
    max_risk_after: float | None = None
    max_risk_delta: float | None = Field(
        default=None,
        description="revised - baseline nos scores máximos ativos.",
    )
    heuristic_threats: HeuristicThreatDeltaSection = Field(default_factory=HeuristicThreatDeltaSection)
    framework_ref_counts: list[FrameworkRefCountDelta] = Field(default_factory=list)
    pack_control_hints: PackHintsDelta = Field(default_factory=PackHintsDelta)
    methodology_insights: MethodologyInsightsDelta | None = None
    trust_boundary_findings: TrustBoundaryFindingDelta | None = None
    structural_findings: StructuralFindingDelta | None = None
    signature_remap_hints: list[str] = Field(
        default_factory=list,
        description="Texto explicativo quando IDs diferem mas assinatura coincide.",
    )


class RiskDeltaSummary(BaseModel):
    analysis_max_score_baseline: float | None = None
    analysis_max_score_revised: float | None = None
    analysis_max_score_delta: float | None = None
    heuristic_increased_ids: list[str] = Field(default_factory=list)
    heuristic_decreased_ids: list[str] = Field(default_factory=list)
    document_residual_aggregate_changed: bool = False


class ThreatDeltaSummary(BaseModel):
    canonical: IdListSectionDiff = Field(
        default_factory=IdListSectionDiff,
        description="Ameaças persistidas no YAML (document.threats).",
    )
    heuristic: HeuristicThreatDeltaSection = Field(default_factory=HeuristicThreatDeltaSection)


class RecommendationDelta(BaseModel):
    pack_hints_added: list[str] = Field(default_factory=list)
    pack_hints_removed: list[str] = Field(default_factory=list)
    framework_catalog_deltas: list[FrameworkRefCountDelta] = Field(default_factory=list)
    methodology_insight_blocks_added: list[str] = Field(default_factory=list)
    methodology_insight_blocks_removed: list[str] = Field(default_factory=list)


class ThreatModelComparisonResult(BaseModel):
    """
    Resultado unificado: estrutura canónica + opcional análise + agregados acionáveis.

    `structural` mantém o contrato já exposto em `/v1/models/diff`.
    """

    summary: ComparisonSummary
    aggregate: DiffAggregate
    structural: ThreatModelDiff
    structural_insights: list[str] = Field(default_factory=list)
    analysis: AnalysisDiff | None = None
    analysis_insights: list[str] = Field(default_factory=list)
    risk_delta: RiskDeltaSummary = Field(default_factory=RiskDeltaSummary)
    threat_delta: ThreatDeltaSummary = Field(default_factory=ThreatDeltaSummary)
    recommendation_delta: RecommendationDelta = Field(default_factory=RecommendationDelta)
    key_insights: list[str] = Field(
        default_factory=list,
        description="Lista priorizada para humanos (estrutura + análise).",
    )
    meta: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadados extensíveis (versão do contrato de diff, etc.).",
    )
    explanations: list[ExplanationRecord] = Field(
        default_factory=list,
        description="Explicabilidade estruturada (mudança principal, risco, metodologia).",
    )
