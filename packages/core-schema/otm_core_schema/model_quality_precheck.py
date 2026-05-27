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


def _has_business_objectives(doc: ThreatModelDocument) -> bool:
    bc = doc.business_context
    return bool(bc and (bc.business_objectives or bc.business_goals))


def _count_rich_flows(doc: ThreatModelDocument) -> int:
    return sum(
        1
        for f in doc.data_flows
        if f.semantic_class.value != "generic"
        or f.public_exposure is not None
        or (f.data_types and len(f.data_types) > 0)
    )


def _count_rich_components(doc: ThreatModelDocument) -> int:
    return sum(
        1 for c in doc.components if c.responsibility or c.privilege_level or c.handles_sensitive_data is not None
    )


def _count_classified_assets(doc: ThreatModelDocument) -> int:
    return sum(
        1 for a in doc.assets if a.data_classification is not None or (a.sensitivity and len(a.sensitivity) > 2)
    )


# Each criterion returns (structure_delta, context_delta, check). Collecting them in a list
# keeps the main assessor branch-free (the cognitive complexity used to live in 6 if/else blocks).
def _check_assets(doc: ThreatModelDocument) -> tuple[int, int, QualityCheckItem]:
    if doc.assets:
        msg = f"{len(doc.assets)} ativo(s) declarado(s)."
        return 12, 10, QualityCheckItem(code="assets_present", passed=True, message=msg)
    return 0, 0, QualityCheckItem(
        code="assets_present",
        passed=False,
        message="Nenhum ativo — priorização e NIST data-centric ficam fracas.",
    )


def _check_trust_boundaries(doc: ThreatModelDocument) -> tuple[int, int, QualityCheckItem]:
    if doc.trust_boundaries:
        validated = sum(1 for b in doc.trust_boundaries if b.user_validated is True)
        msg = f"{len(doc.trust_boundaries)} fronteira(s); {validated} validada(s) pelo modelador."
        return 16, 0, QualityCheckItem(code="trust_boundaries", passed=True, message=msg)
    return 0, 0, QualityCheckItem(
        code="trust_boundaries",
        passed=False,
        message="Sem trust boundaries — cruzamentos de perímetro sub-representados.",
    )


def _check_flow_semantics(doc: ThreatModelDocument, rich_flows: int) -> tuple[int, int, QualityCheckItem]:
    if rich_flows > 0:
        passed = rich_flows >= len(doc.data_flows) // 2 or rich_flows >= 2
        msg = f"{rich_flows} fluxo(s) com semântica ou exposição explícita."
        return min(22, 4 + rich_flows * 4), 0, QualityCheckItem(code="flow_semantics", passed=passed, message=msg)
    return 0, 0, QualityCheckItem(
        code="flow_semantics",
        passed=False,
        message="Fluxos majoritariamente genéricos — achados tendem a ser genéricos.",
    )


def _check_component_context(rich_components: int) -> tuple[int, int, QualityCheckItem]:
    if rich_components > 0:
        msg = f"{rich_components} componente(s) com responsabilidade/privilégio explícitos."
        return (
            min(20, 4 + rich_components * 3),
            0,
            QualityCheckItem(code="component_context", passed=rich_components >= 2, message=msg),
        )
    return 0, 0, QualityCheckItem(
        code="component_context",
        passed=False,
        message="Componentes sem metadata de função/privilégio.",
    )


def _check_business_context(doc: ThreatModelDocument) -> tuple[int, int, QualityCheckItem]:
    if _has_business_objectives(doc):
        return 0, 18, QualityCheckItem(
            code="business_context",
            passed=True,
            message="Objetivos de negócio ou goals declarados.",
        )
    return 0, 0, QualityCheckItem(
        code="business_context",
        passed=False,
        message="Sem objetivos de negócio — PASTA/risk-centric degradam.",
    )


def _check_data_classification(doc: ThreatModelDocument, classified: int) -> tuple[int, int, QualityCheckItem]:
    if classified > 0:
        msg = f"{classified} ativo(s) com classificação ou sensibilidade."
        return 0, 20, QualityCheckItem(code="data_classification", passed=True, message=msg)
    return 0, 0, QualityCheckItem(
        code="data_classification",
        passed=bool(doc.assets),
        message="Classificação de dados ausente ou só textual — NIST DC pode ser ruidoso.",
    )


def _legacy_linear_score(doc: ThreatModelDocument, rich_flows: int, rich_components: int, classified: int) -> int:
    """Eixo legado (soma histórica) — mantém compatibilidade com benchmarks e exportações."""
    legacy = 0
    if doc.assets:
        legacy += 18
    if doc.trust_boundaries:
        legacy += 18
    if rich_flows > 0:
        legacy += min(20, 5 + rich_flows * 3)
    if rich_components > 0:
        legacy += min(18, 6 + rich_components * 2)
    if _has_business_objectives(doc):
        legacy += 12
    if classified > 0:
        legacy += 14
    return min(100, legacy)


def _blend_display_score(legacy_linear: int, overall: int, matrix_level: str) -> int:
    # Peso do legado um pouco maior para modelos muito completos continuarem na banda «rich».
    display = min(100, max(0, int(round(legacy_linear * 0.36 + overall * 0.64))))
    # Modelos muito completos no eixo legado com matriz «strong» não devem cair para «good» no limiar.
    if legacy_linear >= 78 and matrix_level == "strong" and overall >= 52:
        display = max(display, 75)
    return display


def _fit_reasons(meth: str, matrix_level: str) -> list[str]:
    reasons = [f"Metodologia do documento: `{meth}`; matriz de aderência: `{matrix_level}`."]
    if matrix_level == "strong":
        reasons.append("Contexto mínimo para esta metodologia parece suficiente.")
    elif matrix_level == "partial":
        reasons.append("Faltam elementos para classificar como 'strong' (ver matriz por metodologia no relatório).")
    else:
        reasons.append(
            "Metodologia declarada exige mais contexto (objectivos, ativos classificados, privacidade, etc.)."
        )
    return reasons


def _band_for(display_score: int) -> Literal["minimal", "good", "rich"]:
    if display_score >= 73:
        return "rich"
    if display_score >= 48:
        return "good"
    return "minimal"


def _confidence_for(display_score: int, fit: str) -> Literal["low", "medium", "high"]:
    if display_score >= 70 and fit == "strong":
        return "high"
    if display_score >= 40:
        return "medium"
    return "low"


def assess_model_precheck(doc: ThreatModelDocument) -> ModelQualityPrecheck:
    """
    Heurística leve: pontuação e banda para orientar o modelador.

    `methodology_fit` espelha a célula da matriz para a metodologia **declarada** no documento,
    evitando contradições do tipo matrix=strong vs fit=weak sem explicação.
    """
    rich_flows = _count_rich_flows(doc)
    rich_components = _count_rich_components(doc)
    classified = _count_classified_assets(doc)

    structure = 0
    context = 0
    checks: list[QualityCheckItem] = []
    for struct_delta, ctx_delta, item in (
        _check_assets(doc),
        _check_trust_boundaries(doc),
        _check_flow_semantics(doc, rich_flows),
        _check_component_context(rich_components),
        _check_business_context(doc),
        _check_data_classification(doc, classified),
    ):
        structure += struct_delta
        context += ctx_delta
        checks.append(item)

    matrix = build_methodology_fit_matrix(doc)
    meth = doc.model_info.methodology.value
    matrix_level = matrix.get(meth, "partial")
    fit: Literal["strong", "partial", "weak"] = matrix_level  # type: ignore[assignment]

    methodology_points = _fit_to_methodology_points(matrix_level)
    structure = min(100, structure)
    context = min(100, context)
    overall = int(round(structure * 0.44 + methodology_points * 0.28 + context * 0.28))

    legacy_linear = _legacy_linear_score(doc, rich_flows, rich_components, classified)
    display_score = _blend_display_score(legacy_linear, overall, matrix_level)

    return ModelQualityPrecheck(
        score_0_100=display_score,
        band=_band_for(display_score),
        methodology_fit=fit,
        recommendation_confidence=_confidence_for(display_score, fit),
        checks=checks,
        methodology_fit_matrix=matrix,
        structure_score=structure,
        methodology_score=methodology_points,
        context_score=context,
        overall_score=overall,
        methodology_fit_reasons=_fit_reasons(meth, matrix_level),
    )
