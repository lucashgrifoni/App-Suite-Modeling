"""
Pré-check de completude e riqueza do modelo (sem executar o motor).

Usado por API/CLI/UI para feedback antes da análise profunda.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from otm_core_schema.document import ThreatModelDocument
from otm_core_schema.methodology_fit_matrix import build_methodology_fit_matrix


class QualityCheckItem(BaseModel):
    """Um critério avaliado."""

    code: str
    passed: bool
    message: str


class ModelQualityPrecheck(BaseModel):
    """Resultado do pré-check — não substitui análise de risco."""

    score_0_100: int = Field(..., ge=0, le=100)
    band: Literal["minimal", "good", "rich"]
    methodology_fit: Literal["strong", "partial", "weak"]
    recommendation_confidence: Literal["low", "medium", "high"]
    checks: list[QualityCheckItem]
    methodology_fit_matrix: dict[str, str] = Field(
        default_factory=dict,
        description="Adequação por metodologia (stride, pasta, nist_data_centric, …).",
    )


def assess_model_precheck(doc: ThreatModelDocument) -> ModelQualityPrecheck:
    """
    Heurística leve: pontuação e banda para orientar o modelador.
    """
    checks: list[QualityCheckItem] = []
    score = 0

    if doc.assets:
        score += 18
        checks.append(
            QualityCheckItem(
                code="assets_present",
                passed=True,
                message=f"{len(doc.assets)} ativo(s) declarado(s).",
            )
        )
    else:
        checks.append(
            QualityCheckItem(
                code="assets_present",
                passed=False,
                message="Nenhum ativo — priorização e NIST data-centric ficam fracas.",
            )
        )

    if doc.trust_boundaries:
        score += 18
        validated = sum(1 for b in doc.trust_boundaries if b.user_validated is True)
        checks.append(
            QualityCheckItem(
                code="trust_boundaries",
                passed=True,
                message=f"{len(doc.trust_boundaries)} fronteira(s); {validated} validada(s) pelo modelador.",
            )
        )
    else:
        checks.append(
            QualityCheckItem(
                code="trust_boundaries",
                passed=False,
                message="Sem trust boundaries — cruzamentos de perímetro sub-representados.",
            )
        )

    rich_flows = sum(
        1
        for f in doc.data_flows
        if f.semantic_class.value != "generic"
        or f.public_exposure is not None
        or (f.data_types and len(f.data_types) > 0)
    )
    if rich_flows > 0:
        score += min(20, 5 + rich_flows * 3)
        checks.append(
            QualityCheckItem(
                code="flow_semantics",
                passed=rich_flows >= len(doc.data_flows) // 2 or rich_flows >= 2,
                message=f"{rich_flows} fluxo(s) com semântica ou exposição explícita.",
            )
        )
    else:
        checks.append(
            QualityCheckItem(
                code="flow_semantics",
                passed=False,
                message="Fluxos majoritariamente genéricos — achados tendem a ser genéricos.",
            )
        )

    rich_components = sum(
        1
        for c in doc.components
        if c.responsibility or c.privilege_level or c.handles_sensitive_data is not None
    )
    if rich_components > 0:
        score += min(18, 6 + rich_components * 2)
        checks.append(
            QualityCheckItem(
                code="component_context",
                passed=rich_components >= 2,
                message=f"{rich_components} componente(s) com responsabilidade/privilégio explícitos.",
            )
        )
    else:
        checks.append(
            QualityCheckItem(
                code="component_context",
                passed=False,
                message="Componentes sem metadata de função/privilégio.",
            )
        )

    if doc.business_context and (
        doc.business_context.business_objectives or doc.business_context.business_goals
    ):
        score += 12
        checks.append(
            QualityCheckItem(
                code="business_context",
                passed=True,
                message="Objetivos de negócio ou goals declarados.",
            )
        )
    else:
        checks.append(
            QualityCheckItem(
                code="business_context",
                passed=False,
                message="Sem objetivos de negócio — PASTA/risk-centric degradam.",
            )
        )

    classified = sum(
        1
        for a in doc.assets
        if a.data_classification is not None or (a.sensitivity and len(a.sensitivity) > 2)
    )
    if classified > 0:
        score += 14
        checks.append(
            QualityCheckItem(
                code="data_classification",
                passed=True,
                message=f"{classified} ativo(s) com classificação ou sensibilidade.",
            )
        )
    else:
        checks.append(
            QualityCheckItem(
                code="data_classification",
                passed=bool(doc.assets),
                message="Classificação de dados ausente ou só textual — NIST DC pode ser ruidoso.",
            )
        )

    score = min(100, score)
    if score >= 75:
        band: Literal["minimal", "good", "rich"] = "rich"
    elif score >= 45:
        band = "good"
    else:
        band = "minimal"

    meth = doc.model_info.methodology.value
    fit: Literal["strong", "partial", "weak"] = "partial"
    if meth == "pasta" and not (doc.business_context and doc.business_context.business_objectives):
        fit = "weak"
    elif meth == "nist_data_centric" and classified == 0:
        fit = "weak"
    elif doc.assets and doc.trust_boundaries and rich_flows >= 2:
        fit = "strong"

    if score >= 70 and fit == "strong":
        conf: Literal["low", "medium", "high"] = "high"
    elif score >= 40:
        conf = "medium"
    else:
        conf = "low"

    return ModelQualityPrecheck(
        score_0_100=score,
        band=band,
        methodology_fit=fit,
        recommendation_confidence=conf,
        checks=checks,
        methodology_fit_matrix=build_methodology_fit_matrix(doc),
    )
