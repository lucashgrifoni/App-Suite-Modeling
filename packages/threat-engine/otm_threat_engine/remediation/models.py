"""
Modelo de backlog de remediação — acionável, não gestor de tarefas.

Separa o contrato estável (`RemediationBacklog`) dos achados (`AnalysisResult`).
"""

from __future__ import annotations

from typing import Literal

from otm_explainability import ExplanationRecord
from pydantic import BaseModel, Field

BACKLOG_CONTRACT_VERSION = "1.0"

FindingKind = Literal["heuristic_threat", "structural", "trust_boundary", "pack_hint"]


class FindingRef(BaseModel):
    """Referência a um achado na origem da análise."""

    kind: FindingKind
    id: str = Field(..., description="ID estável (ex.: id da ameaça heurística ou código estrutural).")


class BacklogItem(BaseModel):
    """
    Uma ação de remediação sugerida — sempre com racional explícito.

    `recommended_owner` é papel lógico (não pessoa); pode ser null se não houver base.
    """

    id: str
    title: str
    description: str
    rationale: str = Field(..., description="Porque esta ação foi gerada.")
    related_findings: list[FindingRef] = Field(default_factory=list)
    related_components: list[str] = Field(
        default_factory=list,
        description="IDs de componentes canónicos afectados.",
    )
    component_labels: list[str] = Field(
        default_factory=list,
        description="Nomes humanos quando o documento está disponível.",
    )
    methodology_context: str | None = Field(
        default=None,
        description="Metodologia/pack que enquadra o achado.",
    )
    suggested_control_type: str = Field(
        ...,
        description="Tipo de controlo sugerido (valor estável p.ex. identity_access).",
    )
    control_category: str = Field(
        ...,
        description="Dimensão para agrupamento (transversal, dados, exposição, etc.).",
    )
    grouped_root_cause: str = Field(
        ...,
        description="Chave de causa raiz heurística (ex.: weak_authentication_pattern).",
    )
    architecture_layer: str | None = Field(
        default=None,
        description="edge | application | data | integration | governance — quando inferível.",
    )
    priority_rank: int = Field(..., ge=1, description="1 = mais prioritário neste lote.")
    priority_label: Literal["urgent", "high", "medium", "low"]
    priority_explanation: str
    effort_estimate: Literal["low", "medium", "high"]
    impact_estimate: Literal["low", "medium", "high"]
    recommended_owner: str | None = Field(
        default=None,
        description="Papel lógico sugerido (ex.: application_team); null se incerto.",
    )
    owner_explanation: str = Field(
        ...,
        description="Porque este owner foi sugerido ou porque ficou em aberto.",
    )
    quick_win: bool = False
    foundational: bool = False
    urgent: bool = False
    quick_win_explanation: str = ""
    foundational_explanation: str = ""
    next_step: str
    depends_on_action_ids: list[str] = Field(default_factory=list)
    explainability: list[str] = Field(
        default_factory=list,
        description="Lista curta: cobertura, prioridade, limitações do raciocínio.",
    )
    explanations: list[ExplanationRecord] = Field(
        default_factory=list,
        description="Versão estruturada da explicabilidade (contrato partilhado).",
    )


class RemediationBacklog(BaseModel):
    """Resultado agregado: itens + vistas de agrupamento + síntese acionável."""

    schema_version: str = Field(default=BACKLOG_CONTRACT_VERSION)
    document_title: str
    methodology: str
    executive_summary: str
    synergy_notes: list[str] = Field(
        default_factory=list,
        description="Observações transversais (ex.: vários achados com mesma causa raiz).",
    )
    items: list[BacklogItem]
    by_root_cause: dict[str, list[str]] = Field(
        default_factory=dict,
        description="grouped_root_cause → ids de itens.",
    )
    by_control_type: dict[str, list[str]] = Field(
        default_factory=dict,
        description="suggested_control_type → ids.",
    )
    by_control_category: dict[str, list[str]] = Field(
        default_factory=dict,
        description="control_category → ids.",
    )
    quick_win_ids: list[str] = Field(default_factory=list)
    foundational_ids: list[str] = Field(default_factory=list)
    high_impact_ids: list[str] = Field(default_factory=list)
    high_effort_ids: list[str] = Field(default_factory=list)
    top_5_action_ids: list[str] = Field(default_factory=list)
