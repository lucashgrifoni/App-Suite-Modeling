"""Mapeamento de excepções de domínio para respostas HTTP consistentes."""

from __future__ import annotations

import math
from typing import Any, cast

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from otm_api.api_error_messages import msg_request_validation_error

# Cap a single string/bytes echo at this many characters; anything beyond is
# replaced with a suffix that names the suppressed length. Keeps 422 responses
# bounded even when a client sends MB-sized fields, while preserving enough
# context for the user to identify the offending input.
_MAX_INPUT_CHARS = 256


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


def _non_finite_text(value: float) -> str:
    """Nome JSON-ish do float não finito, para o cliente reconhecer o que enviou."""
    if math.isnan(value):
        return "NaN"
    if value > 0:
        return "Infinity"
    return "-Infinity"


def _truncate(value: Any, *, depth: int = 0) -> Any:
    if depth > 4:
        return "…[deep value suppressed]"
    if isinstance(value, str):
        if len(value) <= _MAX_INPUT_CHARS:
            return value
        suppressed = len(value) - _MAX_INPUT_CHARS
        return f"{value[:_MAX_INPUT_CHARS]}…[{suppressed} chars suppressed]"
    if isinstance(value, bytes):
        if len(value) <= _MAX_INPUT_CHARS:
            return value.decode("utf-8", "replace")
        decoded_head = value[:_MAX_INPUT_CHARS].decode("utf-8", "replace")
        suppressed = len(value) - _MAX_INPUT_CHARS
        return f"{decoded_head}…[{suppressed} bytes suppressed]"
    if isinstance(value, (list, tuple)):
        seq = list(value)
        if len(seq) > 50:
            list_head: list[Any] = [_truncate(v, depth=depth + 1) for v in seq[:50]]
            list_head.append(f"…[{len(seq) - 50} items suppressed]")
            return list_head
        return [_truncate(v, depth=depth + 1) for v in seq]
    if isinstance(value, dict):
        if len(value) > 50:
            dict_head_items = list(value.items())[:50]
            out: dict[str, Any] = {str(k): _truncate(v, depth=depth + 1) for k, v in dict_head_items}
            out["__suppressed__"] = f"{len(value) - 50} keys suppressed"
            return out
        return {str(k): _truncate(v, depth=depth + 1) for k, v in value.items()}
    # `NaN`/`Infinity` não são JSON (RFC 8259) e o `JSONResponse` serializa com
    # `allow_nan=False`. O `json.dumps` da stdlib emite estes literais por omissão, por isso
    # um cliente Python com um float NaN nos dados envia-os sem fazer nada de exótico: deixá-los
    # passar rebentava *dentro* deste handler de 422 e o cliente recebia um 500 opaco.
    if isinstance(value, float) and not math.isfinite(value):
        return _non_finite_text(value)
    # JSON scalars pass through untouched (`bool` is a subclass of `int`).
    if isinstance(value, (int, float, type(None))):
        return value
    # Tudo o resto vira texto. A armadilha: para um validador customizado
    # (`raise ValueError(...)` num `@model_validator`), o Pydantic guarda o objeto
    # `Exception` em `ctx['error']`. Se ele chegasse ao `JSONResponse`, o `json.dumps`
    # rebentaria *dentro* deste handler de 422 e o cliente receberia um 500 genérico,
    # perdendo a mensagem do validador. Nunca deixar sair daqui um valor não-serializável.
    return _truncate(str(value), depth=depth)


def _truncated_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for err in errors:
        new_err = dict(err)
        if "input" in new_err:
            new_err["input"] = _truncate(new_err["input"])
        if "ctx" in new_err and isinstance(new_err["ctx"], dict):
            new_err["ctx"] = _truncate(new_err["ctx"])
        out.append(new_err)
    return out


def request_validation_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=problem_detail(
            code="REQUEST_VALIDATION_ERROR",
            message=msg_request_validation_error(),
            status_code=422,
            errors=_truncated_errors(cast(list[dict[str, Any]], exc.errors())),
        ),
    )
