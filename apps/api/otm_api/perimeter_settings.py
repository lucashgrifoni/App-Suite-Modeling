"""
Perímetro opcional: chave de API e limite de taxa (env).

Retrocompatível: sem variáveis definidas, o comportamento permanece o de desenvolvimento local aberto.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from otm_api.cors_settings import CorsProfile, resolve_cors_profile


def _truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in ("1", "true", "yes", "on")


@dataclass(frozen=True)
class ApiKeyPerimeter:
    """Estado efetivo do perímetro de chave de API."""

    enforced: bool
    secret: str | None
    misconfigured: bool


def resolve_api_key_perimeter() -> ApiKeyPerimeter:
    """
    Lê ``OTM_API_KEY`` e diz três coisas distintas: se o perímetro está ligado, qual o
    segredo utilizável, e se a variável está definida mas inutilizável.

    A distinção existe porque ``OTM_API_KEY`` **definido mas em branco** — segredo de CI que
    resolveu para vazio, linha ``.env`` com um espaço a mais, secret k8s com uma newline —
    era colapsado pelo ``strip()`` em "não definido" e abria ``/v1/*`` a qualquer cliente,
    sem uma linha de log a dizê-lo. A intenção do operador aqui é inequívoca (quer o
    perímetro ligado), por isso o perímetro fica ligado e nenhuma credencial serve: falha
    fechado, ruidosamente, em vez de falhar aberto em silêncio.
    """
    raw = os.environ.get("OTM_API_KEY")
    if raw is None:
        return ApiKeyPerimeter(enforced=False, secret=None, misconfigured=False)
    secret = raw.strip()
    if not secret:
        return ApiKeyPerimeter(enforced=True, secret=None, misconfigured=True)
    return ApiKeyPerimeter(enforced=True, secret=secret, misconfigured=False)


def resolve_optional_api_secret() -> str | None:
    """
    Segredo configurado em ``OTM_API_KEY``. Quando definido (não vazio), pedidos a ``/v1/*``
    exigem cabeçalho ``X-OTM-API-Key`` ou ``Authorization: Bearer <token>``.
    """
    return resolve_api_key_perimeter().secret


def resolve_rate_limit_default() -> str | None:
    """
    Expressão de limite (ex.: ``120/minute``), no formato da biblioteca ``limits``.
    Omissão = sem limite global.

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


def describe_effective_perimeter(
    *,
    profile: CorsProfile,
    api_key: ApiKeyPerimeter,
    rate_limit: str | None,
) -> str:
    """
    Uma linha que declara o perímetro com que o processo arrancou.

    Sem ela, o log de arranque de um servidor aberto por engano é indistinguível do de um
    servidor protegido: a única diferença observável era o 401 que o operador nunca vê.
    Vai na mensagem (e não em ``extra``) porque o formatador JSON só promove um conjunto
    fixo de campos — ver `observability._JsonFormatter`.
    """
    if api_key.misconfigured:
        key_state = "misconfigured"
    elif api_key.enforced:
        key_state = "enforced"
    else:
        key_state = "off"
    return (
        "api_perimeter "
        f"environment={profile.environment} "
        f"api_key={key_state} "
        f"rate_limit={rate_limit or 'off'} "
        f"cors_origins={len(profile.origins)}"
    )
