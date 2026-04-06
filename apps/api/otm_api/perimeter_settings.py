"""
Perímetro opcional: chave de API e limite de taxa (env).

Retrocompatível: sem variáveis definidas, o comportamento permanece o de desenvolvimento local aberto.
"""

from __future__ import annotations

import os

from otm_api.cors_settings import resolve_cors_profile


def _truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


def resolve_optional_api_secret() -> str | None:
    """
    Segredo configurado em ``OTM_API_KEY``. Quando definido (não vazio), pedidos a ``/v1/*``
    exigem cabeçalho ``X-OTM-API-Key`` ou ``Authorization: Bearer <token>``.
    """
    raw = (os.environ.get("OTM_API_KEY") or "").strip()
    return raw or None


def resolve_rate_limit_default() -> str | None:
    """
    Expressão SlowAPI (ex.: ``120/minute``). Omissão = sem limite global.

    - ``OTM_RATE_LIMIT_DISABLED=1``: desativa sempre.
    - ``OTM_RATE_LIMIT``: força o limite (útil em dev para testar).
    - Sem variáveis: em ``development`` não há limite; em ``staging``/``production`` usa ``120/minute``.
    """
    if _truthy("OTM_RATE_LIMIT_DISABLED"):
        return None
    explicit = (os.environ.get("OTM_RATE_LIMIT") or "").strip()
    if explicit:
        return explicit
    profile = resolve_cors_profile()
    if profile.environment == "development":
        return None
    return "120/minute"
