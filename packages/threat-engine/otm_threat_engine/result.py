"""Resultado estruturado da análise — consumível por CLI, API e exportadores."""

from __future__ import annotations

from typing import Any, Literal

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
    aggregate_risk: dict[str, Any] | None = Field(
        default=None,
        description="Consolidação agregada de severidades, tops e temas (serializável JSON).",
    )
    decision_cockpit: dict[str, Any] | None = Field(
        default=None,
        description="Resumo executivo de postura e próximos passos.",
    )


def _subject_of(threat: HeuristicThreat) -> str:
    if threat.target_component_id is not None:
        return f"component `{threat.target_component_id}`"
    if threat.target_data_flow_id is not None:
        return f"data flow `{threat.target_data_flow_id}`"
    if threat.target_asset_id is not None:
        return f"asset `{threat.target_asset_id}`"
    return "the model as a whole"


class ThreatIdCollisionError(ValueError):
    """Dois sujeitos distintos reclamam o mesmo id de ameaça.

    Subclasse de `ValueError` de propósito: era isso que `assert_threat_ids_are_injective` lançava,
    e há testes e chamadores que dependem disso. O que muda é haver um tipo que a API e o CLI
    possam apanhar **sem** apanhar todo e qualquer `ValueError` vindo do motor -- porque sem ele
    ninguém a apanhava, e a recusa chegava ao utilizador como 500 INTERNAL_ERROR de um lado e como
    traceback do Python do outro, apesar de a entrada ser corrigível por quem a enviou. Ver
    `tests/test_p3_threat_id_collision_reaches_the_user.py`.

    Os sujeitos ficam em atributos, e não só no texto, para que quem traduz a recusa os possa
    nomear sem voltar a analisar a mensagem.
    """

    def __init__(self, *, threat_id: str, first: str, second: str) -> None:
        self.threat_id = threat_id
        self.first = first
        self.second = second
        super().__init__(
            f"threat id `{threat_id}` is claimed by two different subjects: "
            f"{first} and {second}. "
            "Threat ids are built by joining the subject id with `_`, so these two are "
            "indistinguishable downstream — the CI drift gate, the analysis diff and the "
            "SARIF fingerprints would silently keep only one of them. "
            "Rename one of the two subjects so the ids no longer collide."
        )


def assert_threat_ids_are_injective(heuristics: list[HeuristicThreat]) -> None:
    """Recusa um modelo em que dois sujeitos distintos reclamam o mesmo id de ameaça.

    Os ids são construídos por concatenação com `_`, e `_` é legal dentro de um id de entidade:
    `eng_{comp.id}_{stride}` e `eng_flow_{flow.id}_{stride}` partilham um espaço de nomes plano,
    por isso um componente `flow_svc` e um fluxo `svc` produzem a mesma string. O validador
    `_unique_ids` do schema corre por lista e nunca compara componentes com fluxos, portanto o
    documento é **válido** — a ambiguidade nasce aqui, no esquema de ids, e é aqui que se recusa.
    `custom_rules` tem a mesma forma: regra `a` sobre `b_c` colide com regra `a_b` sobre `c`.

    Três consumidores colapsavam o par **em silêncio**: `analysis_diff` constrói `{h.id: h}` e o
    último vencia; `merge_heuristic_threats` saltava o segundo sem diagnóstico; e o SARIF usa o id
    como `partialFingerprints.otmThreatId`, a identidade do alerta no GitHub code scanning. O
    efeito prático era o gate de drift julgar uma ameaça **substituída** em vez de acrescentada.

    Recusar em vez de renomear é deliberado. Tornar a junção injetiva mudaria **todos** os ids,
    invalidando os fingerprints SARIF e todas as baselines guardadas — a primeira execução após a
    atualização reportaria cada ameaça como nova e faria disparar os gates de toda a gente. Quem
    não tem colisão não paga nada por esta correção; quem tem, tem um modelo genuinamente ambíguo
    e recebe os dois sujeitos por escrito.
    """
    seen: dict[str, HeuristicThreat] = {}
    for threat in heuristics:
        previous = seen.get(threat.id)
        if previous is not None:
            raise ThreatIdCollisionError(
                threat_id=threat.id,
                first=_subject_of(previous),
                second=_subject_of(threat),
            )
        seen[threat.id] = threat
