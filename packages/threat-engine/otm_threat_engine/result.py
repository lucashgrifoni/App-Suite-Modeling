"""Resultado estruturado da análise — consumível por CLI, API e exportadores."""

from __future__ import annotations

from typing import Literal

from otm_core_schema import FrameworkRef, RiskAssessment, StrideCategory, ThreatModelMethodology
from otm_core_schema.enums import HeuristicTier, MethodologyCompletenessState
from otm_core_schema.model_quality_precheck import ModelQualityPrecheck
from otm_explainability import ExplanationRecord
from pydantic import BaseModel, Field

from otm_threat_engine.anti_pattern_library import AntiPatternHit
from otm_threat_engine.wizard_audit_models import WizardSignalTraceEntry


class StructuralFinding(BaseModel):
    """Aviso ou achado de consistência (além da validação Pydantic do documento)."""

    code: str = Field(..., description="Identificador estável para automação e testes.")
    severity: Literal["info", "warning"] = "warning"
    message: str


class TrustBoundaryFinding(BaseModel):
    """Insight sobre fronteiras (ex.: fluxo que as atravessa)."""

    code: str
    message: str
    data_flow_id: str | None = None
    from_boundary_id: str | None = None
    to_boundary_id: str | None = None


class HeuristicThreat(BaseModel):
    """
    Ameaça sugerida pelo motor (heurística STRIDE).
    Pode ser convertida em `Threat` canónico via `merge.merge_heuristic_threats`.
    """

    id: str
    title: str
    description: str
    stride: StrideCategory
    target_component_id: str | None = None
    target_data_flow_id: str | None = None
    target_asset_id: str | None = None
    risk: RiskAssessment
    skipped_as_duplicate: bool = Field(
        default=False,
        description="True se já existia ameaça semelhante no documento.",
    )
    framework_refs: list[FrameworkRef] = Field(
        default_factory=list,
        description="Controles/normas associados (catálogo STRIDE → framework).",
    )
    finding_family: str | None = Field(
        default=None,
        description="Família de achado (ex.: access_control_broken, external_fetch_risk).",
    )
    heuristic_tier: HeuristicTier | None = Field(
        default=None,
        description="Proveniência: genérico, contextual ou padrão composto.",
    )
    signal_refs: list[str] = Field(
        default_factory=list,
        description="Sinais do modelo que dispararam a regra (IDs ou etiquetas).",
    )


class AnalysisSummary(BaseModel):
    """Totais para dashboards e relatórios rápidos."""

    structural_findings: int = 0
    trust_boundary_findings: int = 0
    heuristic_threats_generated: int = 0
    heuristic_threats_skipped_duplicate: int = 0
    pack_threats_generated: int = 0
    pack_threats_skipped_duplicate: int = 0
    max_risk_score: float | None = None
    framework_ref_counts_by_catalog: dict[str, int] = Field(
        default_factory=dict,
        description="Contagem de referências por `FrameworkRef.framework` nas heurísticas.",
    )


class MethodologyInsightBlock(BaseModel):
    """Bloco estruturado para destacar foco metodológico sem quebrar contrato principal."""

    key: str = Field(..., description="Identificador estável do bloco.")
    title: str
    items: list[str] = Field(default_factory=list)


class MethodologyInsights(BaseModel):
    """Complemento opcional da análise com visão específica da metodologia escolhida."""

    profile: str | None = Field(
        default=None,
        description="Resumo curto do perfil metodológico aplicado (ex.: advanced/risk-centric).",
    )
    blocks: list[MethodologyInsightBlock] = Field(default_factory=list)


class AiLayerAssessment(BaseModel):
    """Uma camada de análise AI (PLOT4ai) com evidência limitada ao texto do documento."""

    layer_id: str = Field(..., description="Identificador estável (ex.: retrieval_grounding).")
    label: str
    status: Literal["no_signal", "weak", "moderate", "strong"] = "no_signal"
    evidence: list[str] = Field(
        default_factory=list,
        description="Factos curtos extraídos do modelo — não prova arquitectónica completa.",
    )


class MethodologyCompletenessInfo(BaseModel):
    """Estado explícito quando o contexto não cobre a metodologia escolhida."""

    state: MethodologyCompletenessState
    reasons: list[str] = Field(default_factory=list)
    note: str | None = Field(
        default=None,
        description="Texto curto para relatório (ex.: fallback explícito).",
    )


class AiSystemContextSummary(BaseModel):
    """
    Síntese especializada quando `methodology=plot4ai`.

    Complementa `methodology_insights` com camadas, agrupamento de heurísticas e acções.
    """

    schema_version: str = "1.0"
    synopsis: str = Field(..., description="Resumo honesto do contexto IA inferido.")
    pattern_tags: list[str] = Field(
        default_factory=list,
        description="Etiquetas heurísticas (llm_core, rag, vector_store, …).",
    )
    layers: list[AiLayerAssessment] = Field(default_factory=list)
    primary_risk_surfaces: list[str] = Field(default_factory=list)
    prioritized_recommendations: list[str] = Field(default_factory=list)
    sensitive_data_notes: list[str] = Field(default_factory=list)
    heuristic_ids_by_layer: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Agrupa `plot4ai_*` heuristics por layer_id.",
    )


class AnalysisResult(BaseModel):
    """
    Saída única do motor de análise.
    Não altera o documento de entrada; use `merge` para persistir ameaças novas.
    """

    engine_version: str
    methodology: ThreatModelMethodology = ThreatModelMethodology.STRIDE
    methodology_recommendation_reason: str | None = None
    document_title: str
    structural_findings: list[StructuralFinding] = Field(default_factory=list)
    trust_boundary_findings: list[TrustBoundaryFinding] = Field(default_factory=list)
    heuristic_threats: list[HeuristicThreat] = Field(default_factory=list)
    summary: AnalysisSummary = Field(default_factory=AnalysisSummary)
    methodology_insights: MethodologyInsights | None = None
    industry_pack_id: str | None = None
    pack_control_hints: list[str] = Field(
        default_factory=list,
        description="Sugestões de controlo do pack (relatório / backlog).",
    )
    explanations: list[ExplanationRecord] = Field(
        default_factory=list,
        description="Explicabilidade estruturada (metodologia, achados, risco, fronteiras).",
    )
    ai_system_context: AiSystemContextSummary | None = Field(
        default=None,
        description="Visão PLOT4ai: camadas, superfícies de risco e agrupamento de achados `plot4ai_*`.",
    )
    model_quality_precheck: ModelQualityPrecheck | None = Field(
        default=None,
        description="Pré-check de completude do modelo (sem substituir auditoria).",
    )
    methodology_completeness: MethodologyCompletenessInfo | None = Field(
        default=None,
        description="Adequação do contexto à metodologia (complete/partial/degraded).",
    )
    wizard_context_notes: list[str] = Field(
        default_factory=list,
        description="Notas explicáveis quando sinais `wz:` do assistente influenciam ranking/corpus.",
    )
    wizard_signal_trace: list[WizardSignalTraceEntry] = Field(
        default_factory=list,
        description="Audit trail compacto: tag → efeito → áreas impactadas (governança / export).",
    )
    anti_pattern_hits: list[AntiPatternHit] = Field(
        default_factory=list,
        description="Anti-padrões de modelagem alinhados ao template_semantic_profile.",
    )
