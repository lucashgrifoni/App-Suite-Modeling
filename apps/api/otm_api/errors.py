"""Mapeamento de excepções de domínio para respostas HTTP consistentes."""

from __future__ import annotations

import json
import math
from typing import Any, cast

from fastapi import Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

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


class SurrogateSafeJSONResponse(JSONResponse):
    """
    `JSONResponse` que sobrevive a um surrogate UTF-16 solto vindo do cliente.

    `{"title": "\\ud800"}` é JSON sintaticamente válido — `json.loads` aceita-o, e
    `JSON.stringify` de um browser emite exatamente isto para uma string com meio par
    substituto. O Pydantic rejeita-o corretamente (`string_unicode`) e a rota levantava o 422
    documentado; era a **serialização** desse 422 que rebentava, porque o valor ofensivo é
    ecoado de volta em `errors[].input` (e pode aparecer em `errors[].loc`, quando o surrogate
    está numa *chave*) e `.encode("utf-8")` recusa surrogates soltos. O cliente recebia um 500
    `INTERNAL_ERROR` opaco em vez do 422 que o produto já tinha calculado.

    `backslashreplace` reescreve o carater como a sequência de escape JSON `\\ud800`: continua a
    ser o mesmo code point para quem faça `JSON.parse`/`json.loads`, portanto o utilizador vê
    o valor que enviou, e nenhum outro carater é afetado (UTF-8 codifica tudo o resto).
    """

    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8", "backslashreplace")


def request_validation_handler(
    _request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    return SurrogateSafeJSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=problem_detail(
            code="REQUEST_VALIDATION_ERROR",
            message=msg_request_validation_error(),
            status_code=422,
            errors=_truncated_errors(cast(list[dict[str, Any]], exc.errors())),
        ),
    )


def _body_is_allowed(status_code: int) -> bool:
    """Estados em que o HTTP proíbe corpo (RFC 9110), tal como o handler do FastAPI trata."""
    return status_code >= 200 and status_code not in (204, 205, 304)


def _unparsable_body_response() -> JSONResponse:
    """
    O `400` genérico do FastAPI para um corpo ilegível, no envelope documentado.

    `fastapi/routing.py` levanta `HTTPException(400, "There was an error parsing the body")`
    para qualquer falha de leitura do corpo que não seja `JSONDecodeError` — por exemplo o
    `RecursionError` de um JSON com 10 000 níveis de aninhamento. `detail` saía como string
    solta: uma **terceira** forma de erro, que `docs/features/API.md` exclui ("Não há exceções
    ao envelope nestas rotas"), e que rebenta com `TypeError: string indices must be integers`
    num cliente escrito contra o contrato — o mesmo defeito já corrigido uma vez no 413.

    A resposta é a do irmão imediato: um corpo que não é JSON válido (`JSONDecodeError`, o
    ramo logo acima no FastAPI) já produz este envelope `REQUEST_VALIDATION_ERROR`/422. As
    duas falhas são a mesma — "o corpo do pedido não se consegue ler" — por isso passam a ser
    indistinguíveis, em vez de diferirem no estado *e* na forma consoante o motivo interno.
    """
    return SurrogateSafeJSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=problem_detail(
            code="REQUEST_VALIDATION_ERROR",
            message=msg_request_validation_error(),
            status_code=422,
            errors=[
                {
                    "type": "body_unparsable",
                    "loc": ["body"],
                    "msg": "Request body could not be parsed",
                }
            ],
        ),
    )


async def http_exception_handler(_request: Request, exc: Exception) -> Response:
    """
    Substitui o handler de `HTTPException` do FastAPI por dois motivos concretos.

    1. Serializa com `SurrogateSafeJSONResponse`: os 422 das rotas transportam o input do
       cliente em `errors[]`, e o handler do FastAPI morria a codificá-lo (ver essa classe).
    2. Converte o `400` de corpo ilegível para o envelope documentado (ver
       `_unparsable_body_response`).

    Tudo o resto passa igual, incluindo o `404`/`405` do router do Starlette para caminhos
    fora da tabela de rotas documentada, que não é o contrato que esta API publica.
    """
    exc = cast(StarletteHTTPException, exc)
    headers = getattr(exc, "headers", None)
    if not _body_is_allowed(exc.status_code):
        return Response(status_code=exc.status_code, headers=headers)
    if exc.status_code == status.HTTP_400_BAD_REQUEST and isinstance(exc.detail, str):
        return _unparsable_body_response()
    return SurrogateSafeJSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers,
    )
