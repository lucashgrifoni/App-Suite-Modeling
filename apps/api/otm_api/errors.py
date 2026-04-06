"""Mapeamento de excepções de domínio para respostas HTTP consistentes."""

from __future__ import annotations

from typing import Any, cast

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from otm_api.api_error_messages import msg_request_validation_error


def problem_detail(
    *,
    code: str,
    message: str,
    status_code: int,
    errors: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "code": code,
        "message": message,
        "status": status_code,
    }
    if errors is not None:
        body["errors"] = errors
    return body


def request_validation_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=problem_detail(
            code="REQUEST_VALIDATION_ERROR",
            message=msg_request_validation_error(),
            status_code=422,
            errors=cast(list[dict[str, Any]], exc.errors()),
        ),
    )
