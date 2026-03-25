from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from otm_core_schema import ThreatModelDocument
from pydantic import ValidationError as PydanticValidationError

from otm_api.services.documents import document_from_payload


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
    """Erro 422 padronizado para payload de documento canônico inválido."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=error_detail(
            code="DOCUMENT_VALIDATION_ERROR",
            message="O documento não cumpre o schema canónico.",
            errors=exc.errors(),
        ),
    )


def raise_analysis_validation_error(exc: PydanticValidationError) -> HTTPException:
    """Erro 422 padronizado quando `analysis` não valida como AnalysisResult."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=error_detail(
            code="ANALYSIS_VALIDATION_ERROR",
            message="O campo analysis não é um AnalysisResult válido.",
            errors=exc.errors(),
        ),
    )


def raise_pack_not_found(exc: FileNotFoundError) -> HTTPException:
    """Erro 404 quando o industry pack pedido não existe."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_detail(code="PACK_NOT_FOUND", message=str(exc)),
    )


def raise_template_not_found(exc: FileNotFoundError) -> HTTPException:
    """Erro 404 quando o template pedido não existe no catálogo embutido."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_detail(code="TEMPLATE_NOT_FOUND", message=str(exc)),
    )


def raise_template_invalid(exc: PydanticValidationError) -> HTTPException:
    """Erro 422 quando o YAML do template não produz documento canónico válido."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=error_detail(
            code="TEMPLATE_INVALID",
            message="O template não produz um documento canónico válido.",
            errors=exc.errors(),
        ),
    )


def document_from_payload_or_422(data: dict[str, Any]) -> ThreatModelDocument:
    try:
        return document_from_payload(data)
    except PydanticValidationError as e:
        raise raise_document_validation_error(e) from e
