"""
Locale para mensagens de erro HTTP user-facing.

Resolvido a partir do cabeçalho ``Accept-Language`` (BCP 47), com allowlist estrita.
Não usar valores arbitrários do corpo do pedido (segurança).

Default sem cabeçalho ou sem match: ``en`` (API OSS).
"""

from __future__ import annotations

import contextvars
import re
from typing import Literal

ApiErrorLocale = Literal["pt-BR", "en"]

_error_locale_ctx: contextvars.ContextVar[ApiErrorLocale] = contextvars.ContextVar(
    "otm_api_error_locale",
    default="en",
)


def get_api_error_locale() -> ApiErrorLocale:
    """Locale activo para a mensagem de erro do pedido corrente."""
    return _error_locale_ctx.get()


def set_api_error_locale_for_request(locale: ApiErrorLocale) -> contextvars.Token[ApiErrorLocale]:
    """Usado pelo middleware; devolve token para ``reset``."""
    return _error_locale_ctx.set(locale)


def reset_api_error_locale(token: contextvars.Token[ApiErrorLocale]) -> None:
    _error_locale_ctx.reset(token)


def resolve_api_error_locale_from_accept_language(header_value: str | None) -> ApiErrorLocale:
    """
    Primeira língua na lista ``Accept-Language`` que corresponda a pt ou en.

    - Qualquer tag ``pt*`` (pt, pt-BR, pt-PT) → ``pt-BR``.
    - Qualquer tag ``en*`` → ``en``.
    - Caso contrário → ``en``.
    """
    if not header_value or not header_value.strip():
        return "en"
    for part in header_value.split(","):
        tag = part.split(";", 1)[0].strip().lower()
        if not tag:
            continue  # pragma: no cover - defensive: empty Accept-Language token skipped
        primary = re.split(r"[-_]", tag, 1)[0]
        if primary == "pt":
            return "pt-BR"
        if primary == "en":
            return "en"
    return "en"
