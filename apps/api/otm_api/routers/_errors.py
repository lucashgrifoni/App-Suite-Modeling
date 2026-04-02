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
    """422 when the canonical document payload is invalid."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=error_detail(
            code="DOCUMENT_VALIDATION_ERROR",
            message="The document does not satisfy the canonical schema.",
            errors=exc.errors(),
        ),
    )


def raise_analysis_validation_error(exc: PydanticValidationError) -> HTTPException:
    """422 when `analysis` is not a valid AnalysisResult."""
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=error_detail(
            code="ANALYSIS_VALIDATION_ERROR",
            message="The analysis field is not a valid AnalysisResult.",
            errors=exc.errors(),
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
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=error_detail(
            code="TEMPLATE_INVALID",
            message="The template does not produce a valid canonical document.",
            errors=exc.errors(),
        ),
    )


def document_from_payload_or_422(data: dict[str, Any]) -> ThreatModelDocument:
    try:
        return document_from_payload(data)
    except PydanticValidationError as e:
        raise raise_document_validation_error(e) from e
