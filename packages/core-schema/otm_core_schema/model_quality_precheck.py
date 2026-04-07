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
    structure_score: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Completude estrutural (componentes, fronteiras, fluxos).",
    )
    methodology_score: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Aderência do modelo à metodologia declarada no documento.",
    )
    context_score: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Riqueza de contexto de negócio e classificação de dados.",
    )
    overall_score: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Combinação explícita (média ponderada) dos três eixos.",
    )
    methodology_fit_reasons: list[str] = Field(
        default_factory=list,
        description="Por que strong/partial/weak para a metodologia efectiva do documento.",
    )


def _fit_to_methodology_points(level: str) -> int:
    # Faixa mais larga para separar casos «ricos na estrutura» vs «aderência fraca à metodologia».
    return {"strong": 94, "partial": 64, "weak": 34}.get(level, 48)


def assess_model_precheck(doc: ThreatModelDocument) -> ModelQualityPrecheck:
    """
    Heurística leve: pontuação e banda para orientar o modelador.

    `methodology_fit` espelha a célula da matriz para a metodologia **declarada** no documento,
    evitando contradições do tipo matrix=strong vs fit=weak sem explicação.
    """
    checks: list[QualityCheckItem] = []
    structure = 0
    context = 0

    if doc.assets:
        structure += 12
        context += 10
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
        structure += 16
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
        structure += min(22, 4 + rich_flows * 4)
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
        1 for c in doc.components if c.responsibility or c.privilege_level or c.handles_sensitive_data is not None
    )
    if rich_components > 0:
        structure += min(20, 4 + rich_components * 3)
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

    if doc.business_context and (doc.business_context.business_objectives or doc.business_context.business_goals):
        context += 18
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
        1 for a in doc.assets if a.data_classification is not None or (a.sensitivity and len(a.sensitivity) > 2)
    )
    if classified > 0:
        context += 20
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

    matrix = build_methodology_fit_matrix(doc)
    meth = doc.model_info.methodology.value
    matrix_level = matrix.get(meth, "partial")
    fit: Literal["strong", "partial", "weak"] = matrix_level  # type: ignore[assignment]

    methodology_points = _fit_to_methodology_points(matrix_level)
    structure = min(100, structure)
    context = min(100, context)
    overall = int(round(structure * 0.44 + methodology_points * 0.28 + context * 0.28))

    # Eixo legado (soma histórica) — mantém compatibilidade com benchmarks e exportações.
    legacy_linear = 0
    if doc.assets:
        legacy_linear += 18
    if doc.trust_boundaries:
        legacy_linear += 18
    if rich_flows > 0:
        legacy_linear += min(20, 5 + rich_flows * 3)
    if rich_components > 0:
        legacy_linear += min(18, 6 + rich_components * 2)
    if doc.business_context and (doc.business_context.business_objectives or doc.business_context.business_goals):
        legacy_linear += 12
    if classified > 0:
        legacy_linear += 14
    legacy_linear = min(100, legacy_linear)

    # Combina eixo legado com o eixo multi-dimensional; peso do legado um pouco maior para
    # modelos muito completos continuarem na banda «rich» sem perder separação nos casos médios.
    display_score = int(round(legacy_linear * 0.36 + overall * 0.64))
    display_score = min(100, max(0, display_score))
    # Modelos muito completos no eixo legado com matriz «strong» para a metodologia declarada
    # não devem cair para «good» só porque o blend numérico ficou no limiar — evita achatamento.
    if legacy_linear >= 78 and matrix_level == "strong" and overall >= 52:
        display_score = max(display_score, 75)

    fit_reasons: list[str] = [
        f"Metodologia do documento: `{meth}`; matriz de aderência: `{matrix_level}`.",
    ]
    if matrix_level == "strong":
        fit_reasons.append("Contexto mínimo para esta metodologia parece suficiente.")
    elif matrix_level == "partial":
        fit_reasons.append("Faltam elementos para classificar como 'strong' (ver matriz por metodologia no relatório).")
    else:
        fit_reasons.append(
            "Metodologia declarada exige mais contexto (objectivos, ativos classificados, privacidade, etc.)."
        )

    if display_score >= 73:
        band: Literal["minimal", "good", "rich"] = "rich"
    elif display_score >= 48:
        band = "good"
    else:
        band = "minimal"

    if display_score >= 70 and fit == "strong":
        conf: Literal["low", "medium", "high"] = "high"
    elif display_score >= 40:
        conf = "medium"
    else:
        conf = "low"

    return ModelQualityPrecheck(
        score_0_100=display_score,
        band=band,
        methodology_fit=fit,
        recommendation_confidence=conf,
        checks=checks,
        methodology_fit_matrix=matrix,
        structure_score=structure,
        methodology_score=methodology_points,
        context_score=context,
        overall_score=overall,
        methodology_fit_reasons=fit_reasons,
    )
