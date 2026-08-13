"""
Modelo de dados do report premium — camada única entre motor/backlog/diff e renderização.

Valores inferidos devem ser apresentados como sugestão, nunca como facto de auditoria.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from .enums import ReportLevel
from .i18n_locale import PremiumReportLocale


class InferenceDisclaimer(BaseModel):
    """Transparência sobre limites de inferência heurística."""

    summary: str = Field(
        ...,
        description="Texto curto: ownership, exploitability e impacto de negócio são sugestões.",
    )
    bullets: list[str] = Field(default_factory=list)


class CoverPage(BaseModel):
    """Capa executiva."""

    title: str
    model_id_hint: str | None = Field(
        default=None,
        description="Identificador derivado do título/metadata quando não há ID externo.",
    )
    document_version: str | None = None
    schema_version: str
    primary_methodology: str
    complementary_methodologies: list[str] = Field(default_factory=list)
    system_type: str
    industry_sector: str
    analysis_date_iso: str
    app_suite_version: str
    overall_risk_label: str
    overall_status: Literal[
        "requires_immediate_attention",
        "action_recommended",
        "acceptable_with_follow_up",
    ]
    overall_status_display: str


class ExecutiveSummaryBlock(BaseModel):
    """Resumo para gestão."""

    threat_count: int
    severity_distribution: dict[str, int]
    methodology_distribution: dict[str, int]
    top_trust_boundaries: list[str]
    top_attack_surfaces: list[str]
    top5_risk_titles: list[str]
    business_impact_summary: str
    urgency_level: Literal["high", "medium", "low"]
    executive_conclusion: str
    readiness_questions: list[str] = Field(
        default_factory=list,
        description="Perguntas objetivas: risco alto?, pronto para release?, etc.",
    )


class ArchitectureSummary(BaseModel):
    """Visão arquitetural resumida."""

    narrative: str
    main_components: list[str]
    main_flows: list[str]
    trust_boundaries: list[str]
    external_dependencies: list[str]
    sensitive_assets: list[str]
    methodology_used: str
    methodology_recommended: str | None = None
    recommendation_reason: str | None = None
    mermaid_flowchart: str | None = Field(
        default=None,
        description="Diagrama Mermaid opcional (deep).",
    )


class DistributionBlock(BaseModel):
    """Estatísticas agregadas."""

    total_threats: int
    by_severity_band: dict[str, int]
    by_stride: dict[str, int]
    by_methodology_tag: dict[str, int]
    by_component: dict[str, int]
    by_trust_boundary: dict[str, int]
    by_risk_type: dict[str, int]
    by_control_domain: dict[str, int]
    heatmap_stride_severity: dict[str, dict[str, int]]
    top_components_ranked: list[tuple[str, float]]
    top_boundaries_ranked: list[tuple[str, float]]


class TopRiskItem(BaseModel):
    """Item na lista priorizada."""

    rank: int
    threat_id: str
    title: str
    methodology: str
    component: str | None
    asset: str | None
    severity_score: float | None
    likelihood: int
    impact: int
    exploitability_summary: str
    business_impact_labels: list[str]
    priority_tier: Literal["P1", "P2", "P3"]
    composite_score: float
    recommended_action: str
    suggested_horizon: Literal["immediate", "short", "medium"]


class RootCauseGroup(BaseModel):
    """Agrupamento por causa raiz (alinhado ao backlog + lens humana)."""

    key: str
    display_name: str
    threat_count: int
    component_ids: list[str]
    suggested_controls: list[str]
    single_fix_recommendation: str


class ExploitabilityProfile(BaseModel):
    """Contexto de exploração — majoritariamente heurístico."""

    threat_id: str
    requires_external_access: bool | None
    requires_authenticated_user: bool | None
    requires_user_interaction: bool | None
    requires_external_integration_control: bool | None
    requires_mitm: bool | None
    requires_webhook_or_deeplink: bool | None
    attack_locality: Literal["local", "remote", "hybrid", "unknown"]
    depends_on_agent_tool_use: bool | None
    depends_on_prompt_or_retrieval_abuse: bool | None
    depends_on_misconfiguration: bool | None
    notes: str


class BusinessImpactRow(BaseModel):
    """Impacto de negócio sugerido."""

    threat_id: str
    labels: list[str]
    rationale: str


class QuickWinItem(BaseModel):
    """Quick win derivado do backlog."""

    backlog_item_id: str
    title: str
    rationale: str


class OwnershipRow(BaseModel):
    """Responsabilidade sugerida."""

    scope: str
    suggested_owner_role: str | None
    explanation: str
    backlog_item_ids: list[str] = Field(default_factory=list)


class RoadmapPhase(BaseModel):
    """Fase do roadmap."""

    phase: Literal["immediate", "short", "medium"]
    title: str
    items: list[str]


class BaselineDiffSection(BaseModel):
    """Diff entre análises (baseline vs atual)."""

    has_baseline: bool
    methodology_changed: bool
    max_risk_delta: float | None
    threats_added: list[str]
    threats_removed: list[str]
    threats_modified: list[str]
    recurring_signatures: list[str]
    trust_boundary_delta_summary: str
    structural_delta_summary: str
    narrative: str
    semantic_improved: list[str] = Field(
        default_factory=list,
        description="Melhorias heurísticas entre análises (não causalidade com YAML).",
    )
    semantic_worsened: list[str] = Field(default_factory=list)
    semantic_risk_impact: list[str] = Field(default_factory=list)
    semantic_insights_from_analysis: list[str] = Field(
        default_factory=list,
        description="Bullets de contexto (precheck, anti-patterns, ranking) entre execuções.",
    )


class DedupeGroup(BaseModel):
    """Deduplicação inteligente."""

    group_key: str
    occurrence_count: int
    threat_ids: list[str]
    components: list[str]
    unified_remediation: str


class ExplainabilitySnippet(BaseModel):
    """Trecho de explainability incluído no report."""

    record_id: str
    category: str
    message: str
    confidence: str | None = None


class StrategicRecommendation(BaseModel):
    """Recomendação estratégica."""

    title: str
    detail: str


#: Contrato da listagem do apêndice: cada ameaça começa uma linha com este prefixo e o corpo vem
#: na linha seguinte. É por aqui que o renderizador HTML volta a ler a listagem como estrutura
#: para montar a tabela do PDF, e é por aqui que se conta quantas entradas ficaram à vista.
APPENDIX_ENTRY_PREFIX = "### "


def count_appendix_entries(listing: str) -> int:
    """Entradas presentes na listagem — linhas iniciadas pelo prefixo, não ocorrências no texto."""
    return sum(1 for line in listing.splitlines() if line.startswith(APPENDIX_ENTRY_PREFIX))


class TechnicalAppendix(BaseModel):
    """Apêndice técnico (deep)."""

    full_threat_listing: str
    total_threat_count: int = Field(
        default=0,
        description=(
            "Ameaças que a análise produziu, antes de qualquer corte. `full_threat_listing` pode "
            "trazer menos (orçamento de tamanho); quem renderiza declara 'N de M' a partir daqui, "
            "e não do comprimento da listagem, que já vem cortada."
        ),
    )
    methodology_outputs_note: str
    import_evidence_note: str | None = None


class GuidedModelingAuditBlock(BaseModel):
    """Eco do cockpit / assistente no report — compacto, auditável, sem duplicar o JSON completo."""

    model_quality_summary_line: str | None = Field(
        default=None,
        description="Uma linha: score pré-check, banda e confiança.",
    )
    methodology_completeness_line: str | None = Field(
        default=None,
        description="Estado e nota curta da completude metodológica.",
    )
    wizard_context_notes: list[str] = Field(default_factory=list)
    wizard_signal_trace_lines: list[str] = Field(default_factory=list)
    top_model_gap_messages: list[str] = Field(default_factory=list)
    anti_pattern_summaries: list[str] = Field(default_factory=list)


class PremiumReportPayload(BaseModel):
    """Payload completo — entrada para Markdown/HTML/PDF."""

    schema_version: str = "1.0"
    locale: PremiumReportLocale = Field(
        default="pt-BR",
        description="Locale dos textos estruturais (pt-BR | en).",
    )
    level: ReportLevel
    disclaimer: InferenceDisclaimer
    cover: CoverPage
    executive_summary: ExecutiveSummaryBlock
    architecture: ArchitectureSummary
    distributions: DistributionBlock
    top_risks: list[TopRiskItem]
    root_cause_groups: list[RootCauseGroup]
    exploitability_profiles: list[ExploitabilityProfile]
    business_impacts: list[BusinessImpactRow]
    quick_wins: list[QuickWinItem]
    ownership: list[OwnershipRow]
    strategic_recommendations: list[StrategicRecommendation]
    roadmap: list[RoadmapPhase]
    baseline_diff: BaselineDiffSection | None
    deduplication: list[DedupeGroup]
    explainability: list[ExplainabilitySnippet]
    technical_appendix: TechnicalAppendix | None = None
    methodology_voice: list[str] = Field(
        default_factory=list,
        description="Notas de adaptação por metodologia dominante.",
    )
    guided_modeling_audit: GuidedModelingAuditBlock | None = Field(
        default=None,
        description="Contexto do assistente, lacunas do pré-check e anti-padrões (alinhado ao export Markdown).",
    )
