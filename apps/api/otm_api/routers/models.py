from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status
from otm_core_schema import diff_documents
from otm_threat_engine import recommend_methodology
from pydantic import ValidationError as PydanticValidationError

from otm_api.routers._errors import (
    document_from_payload_or_422,
    raise_analysis_validation_error,
    raise_pack_not_found,
)
from otm_api.schemas.bodies import (
    AnalyzeBody,
    CompareBody,
    CreateModelResponse,
    DiffBody,
    DocumentBody,
    RecommendMethodologyResponse,
    ValidateResponse,
)
from otm_api.services.analysis import run_analysis
from otm_api.services.compare import comparison_from_validated_documents
from otm_api.services.documents import create_blank_document

router = APIRouter(prefix="/models", tags=["Modelos"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Criar modelo em branco",
    description=(
        "Devolve um `ThreatModelDocument` mínimo válido (equivalente a `otm init` sem template)."
    ),
)
def create_model() -> CreateModelResponse:
    doc = create_blank_document()
    return CreateModelResponse(document=doc.model_dump(mode="json", by_alias=True))


@router.post(
    "/validate",
    summary="Validar modelo",
    description="Valida o payload contra o schema canónico; não persiste dados.",
)
def validate_model(body: DocumentBody) -> ValidateResponse:
    doc = document_from_payload_or_422(body.document)
    return ValidateResponse(
        title=doc.metadata.title,
        schema_version=doc.model_info.schema_version,
        component_count=len(doc.components),
        threat_count=len(doc.threats),
    )


@router.post(
    "/diff",
    summary="Diff entre versões do modelo",
    description=(
        "Compara duas versões canónicas (baseline vs revisão) e devolve diff estruturado. "
        "Implementação em `otm_core_schema.diff_documents` — mesma semântica que `otm diff` na CLI."
    ),
    response_description="Objeto `ThreatModelDiff` serializado em JSON.",
)
def diff_model_versions(body: DiffBody) -> dict[str, Any]:
    baseline = document_from_payload_or_422(body.baseline)
    revised = document_from_payload_or_422(body.revised)
    result = diff_documents(baseline, revised)
    return result.model_dump(mode="json")


@router.post(
    "/compare",
    summary="Comparar modelos (estrutura e opcionalmente análise)",
    description=(
        "Devolve `ThreatModelComparisonResult`: diff canónico, agregados, insights e, se fornecido "
        "`baseline_analysis`/`revised_analysis` ou `run_analysis=true`, delta de risco/heurísticas."
    ),
    response_description="JSON do resultado unificado de comparação.",
)
def compare_models(body: CompareBody) -> dict[str, Any]:
    b_doc = document_from_payload_or_422(body.baseline)
    r_doc = document_from_payload_or_422(body.revised)
    try:
        result = comparison_from_validated_documents(
            b_doc,
            r_doc,
            baseline_analysis=body.baseline_analysis,
            revised_analysis=body.revised_analysis,
            run_analysis_flag=body.run_analysis,
            pack_id=body.pack_id,
        )
    except FileNotFoundError as e:
        raise raise_pack_not_found(e) from e
    except PydanticValidationError as e:
        raise raise_analysis_validation_error(e) from e
    return result.model_dump(mode="json")


@router.post(
    "/recommend-methodology",
    summary="Recomendar metodologia/engine",
    description="Sugere a metodologia com base no contexto do documento.",
)
def recommend_methodology_for_model(body: DocumentBody) -> RecommendMethodologyResponse:
    doc = document_from_payload_or_422(body.document)
    rec = recommend_methodology(doc)
    return RecommendMethodologyResponse(
        methodology=rec.methodology,
        reason=rec.reason,
        explanations=list(rec.explanations),
    )


@router.post(
    "/analyze",
    summary="Analisar modelo",
    description="Executa o motor STRIDE, fronteiras e risco; pack opcional.",
    response_description="Estrutura `AnalysisResult` serializada em JSON.",
)
def analyze_model(body: AnalyzeBody) -> dict[str, Any]:
    doc = document_from_payload_or_422(body.document)
    try:
        result = run_analysis(
            doc,
            pack_id=body.pack_id,
            methodology=body.methodology,
            auto_recommend_methodology=body.auto_recommend_methodology,
        )
    except FileNotFoundError as e:
        raise raise_pack_not_found(e) from e
    return result.model_dump(mode="json")
