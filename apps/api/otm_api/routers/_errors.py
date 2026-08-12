from __future__ import annotations

from typing import Any, cast

from fastapi import HTTPException, status
from otm_core_schema import ThreatModelDocument
from otm_threat_engine import AnalysisResult
from pydantic import ValidationError as PydanticValidationError

from otm_api.api_error_messages import (
    msg_analysis_document_mismatch,
    msg_analysis_validation_error,
    msg_document_validation_error,
    msg_template_invalid,
)
from otm_api.errors import _truncated_errors
from otm_api.services.analysis_pairing import analysis_document_mismatches
from otm_api.services.documents import document_from_payload


def _pydantic_error_items(exc: PydanticValidationError) -> list[dict[str, Any]]:
    """
    Erros no formato esperado pela API, seguros para JSON.

    Com ``include_context=True`` (default), o Pydantic pode incluir em ``ctx``
    objetos ``Exception`` (ex.: ``ValueError`` em validação de referências de
    fluxos). Isso quebra ``JSONResponse`` do FastAPI com TypeError e aparece
    como 500 genérico no cliente.

    O campo ``input`` (e ``ctx``) é truncado com o mesmo limite das respostas
    422 de ``RequestValidationError`` (256 carateres): mantém a resposta
    delimitada perante payloads enormes e evita que estes erros de domínio
    ecoem conteúdo arbitrário não-delimitado de volta ao cliente.
    """
    items = cast(list[dict[str, Any]], exc.errors(include_context=False))
    return _truncated_errors(items)


def error_detail(
    *,
    code: str,
    message: str,
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    detail: dict[str, Any] = {"code": code, "message": message}
    if errors is not None:
        detail["errors"] = errors
    return detail


def raise_document_validation_error(exc: PydanticValidationError) -> HTTPException:
    """422 when the canonical document payload is invalid."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=error_detail(
            code="DOCUMENT_VALIDATION_ERROR",
            message=msg_document_validation_error(),
            errors=_pydantic_error_items(exc),
        ),
    )


def raise_analysis_validation_error(exc: PydanticValidationError) -> HTTPException:
    """422 when `analysis` is not a valid AnalysisResult."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=error_detail(
            code="ANALYSIS_VALIDATION_ERROR",
            message=msg_analysis_validation_error(),
            errors=_pydantic_error_items(exc),
        ),
    )


def ensure_analysis_matches_document(
    document: ThreatModelDocument,
    analysis: AnalysisResult,
    *,
    analysis_field: str = "analysis",
    document_field: str = "document",
) -> None:
    """
    422 quando o `analysis` recebido não foi produzido para o `document` recebido.

    Guarda, não conversor: as rotas que emparelham os dois artefactos chamam-na depois de
    validar cada um. Ver `services/analysis_pairing.py` para o critério e o âmbito.

    Os nomes dos campos são parâmetros porque `/v1/models/compare` recebe **dois** pares e
    tem de dizer qual deles está trocado.
    """
    mismatches = analysis_document_mismatches(
        document,
        analysis,
        analysis_field=analysis_field,
        document_field=document_field,
    )
    if not mismatches:
        return
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=error_detail(
            code="ANALYSIS_DOCUMENT_MISMATCH",
            message=msg_analysis_document_mismatch(analysis_field=analysis_field, document_field=document_field),
            errors=mismatches,
        ),
    )


def raise_pack_not_found(exc: FileNotFoundError) -> HTTPException:
    """404 when the requested industry pack does not exist."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_detail(code="PACK_NOT_FOUND", message=str(exc)),
    )


def raise_template_not_found(exc: FileNotFoundError) -> HTTPException:
    """404 when the template does not exist in the embedded catalog."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_detail(code="TEMPLATE_NOT_FOUND", message=str(exc)),
    )


def raise_template_invalid(exc: PydanticValidationError) -> HTTPException:
    """422 when template YAML does not yield a valid canonical document."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=error_detail(
            code="TEMPLATE_INVALID",
            message=msg_template_invalid(),
            errors=_pydantic_error_items(exc),
        ),
    )


def document_from_payload_or_422(data: dict[str, Any]) -> ThreatModelDocument:
    try:
        return document_from_payload(data)
    except PydanticValidationError as e:
        raise raise_document_validation_error(e) from e


def analysis_from_payload_or_422(data: dict[str, Any] | None) -> AnalysisResult | None:
    """`AnalysisResult` validado, ou `None` quando o campo foi omitido."""
    if data is None:
        return None
    try:
        return AnalysisResult.model_validate(data)
    except PydanticValidationError as e:
        raise raise_analysis_validation_error(e) from e
