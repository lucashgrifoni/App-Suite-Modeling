from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import ValidationError as PydanticValidationError

from otm_api.schemas.bodies import (
    AnalyzeBody,
    CreateModelResponse,
    DocumentBody,
    RecommendMethodologyResponse,
    ValidateResponse,
)
from otm_api.services.analysis import run_analysis
from otm_api.services.documents import create_blank_document, document_from_payload
from otm_threat_engine import recommend_methodology

router = APIRouter(prefix="/models", tags=["Modelos"])


@router.post(
    "",
    response_model=CreateModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar modelo em branco",
    description="Devolve um `ThreatModelDocument` mínimo válido (equivalente a `otm init` sem template).",
)
def create_model() -> CreateModelResponse:
    doc = create_blank_document()
    return CreateModelResponse(document=doc.model_dump(mode="json", by_alias=True))


@router.post(
    "/validate",
    response_model=ValidateResponse,
    summary="Validar modelo",
    description="Valida o payload contra o schema canónico; não persiste dados.",
)
def validate_model(body: DocumentBody) -> ValidateResponse:
    try:
        doc = document_from_payload(body.document)
    except PydanticValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "DOCUMENT_VALIDATION_ERROR",
                "message": "O documento não cumpre o schema canónico.",
                "errors": e.errors(),
            },
        ) from e
    return ValidateResponse(
        title=doc.metadata.title,
        schema_version=doc.model_info.schema_version,
        component_count=len(doc.components),
        threat_count=len(doc.threats),
    )


@router.post(
    "/recommend-methodology",
    response_model=RecommendMethodologyResponse,
    summary="Recomendar metodologia/engine",
    description="Sugere a metodologia com base no contexto do documento.",
)
def recommend_methodology_for_model(body: DocumentBody) -> RecommendMethodologyResponse:
    try:
        doc = document_from_payload(body.document)
    except PydanticValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "DOCUMENT_VALIDATION_ERROR",
                "message": "O documento não cumpre o schema canónico.",
                "errors": e.errors(),
            },
        ) from e
    rec = recommend_methodology(doc)
    return RecommendMethodologyResponse(methodology=rec.methodology, reason=rec.reason)


@router.post(
    "/analyze",
    summary="Analisar modelo",
    description="Executa o motor STRIDE, fronteiras e risco; pack opcional.",
    response_description="Estrutura `AnalysisResult` serializada em JSON.",
)
def analyze_model(body: AnalyzeBody) -> dict[str, Any]:
    try:
        doc = document_from_payload(body.document)
    except PydanticValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "DOCUMENT_VALIDATION_ERROR",
                "message": "O documento não cumpre o schema canónico.",
                "errors": e.errors(),
            },
        ) from e
    try:
        result = run_analysis(
            doc,
            pack_id=body.pack_id,
            methodology=body.methodology,
            auto_recommend_methodology=body.auto_recommend_methodology,
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PACK_NOT_FOUND", "message": str(e)},
        ) from e
    return result.model_dump(mode="json")
