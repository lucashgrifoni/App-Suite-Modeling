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


class TrustedProxyConfigError(ValueError):
    """``OTM_TRUSTED_PROXY`` não foi declarado onde é obrigatório, ou tem um valor desconhecido."""


_TRUSTED_PROXY_BY_VALUE: dict[str, bool] = {
    "1": True,
    "true": True,
    "yes": True,
    "on": True,
    "0": False,
    "false": False,
    "no": False,
    "off": False,
}


def _declared_trusted_proxy() -> bool | None:
    """A declaração do operador, ou ``None`` quando não disse nada.

    Um valor não reconhecido é recusado em vez de lido como ``off``, pelo mesmo motivo que
    ``OTM_ENV=prd`` é recusado: "off" aqui significa "todos os chamadores encaminhados
    partilham um balde", e uma gralha não pode ser a forma de lá chegar. Vazio conta como
    não declarado (secret de CI que resolveu para nada), o que em staging/produção falha
    fechado no arranque em vez de degradar em silêncio.
    """
    raw = (os.environ.get("OTM_TRUSTED_PROXY") or "").strip().lower()
    if not raw:
        return None
    if raw not in _TRUSTED_PROXY_BY_VALUE:
        accepted = ", ".join(sorted(_TRUSTED_PROXY_BY_VALUE))
        raise TrustedProxyConfigError(
            f"OTM_TRUSTED_PROXY={raw!r} is not a recognised value. Accepted: {accepted}. "
            "Refusing to read it as `off`, which would put every forwarded caller in one "
            "shared rate-limit bucket."
        )
    return _TRUSTED_PROXY_BY_VALUE[raw]


def _undeclared_trusted_proxy_error(*, environment: str, rate_limit: str) -> TrustedProxyConfigError:
    """A recusa de arranque, escrita como runbook e não como diagnóstico.

    O operador que a lê está a meio de um deploy e tem de escolher entre duas opções cujas
    consequências são opostas; listar só os valores aceites obrigá-lo-ia a adivinhar qual
    delas descreve a sua infraestrutura, e a errada custa disponibilidade ou o controlo.
    """
    return TrustedProxyConfigError(
        f"OTM_TRUSTED_PROXY is not declared, and this {environment} deployment has the rate limit "
        f"{rate_limit} active. Behind the reverse proxy that docs/architecture/DEPLOYMENT_INVARIANTS.md "
        "makes mandatory, uvicorn rewrites every caller address from X-Forwarded-For before this app "
        "runs, so the app cannot tell one caller from another unless you declare that the proxy is "
        "yours. Pick one: "
        "OTM_TRUSTED_PROXY=1 — a reverse proxy you control is in front, the forwarded address "
        f"identifies the caller, and {rate_limit} applies per caller (requires uvicorn "
        "--proxy-headers --forwarded-allow-ips=<proxy address>); or "
        "OTM_TRUSTED_PROXY=0 — no such proxy, every request carrying X-Forwarded-For is counted in "
        f"ONE shared bucket, so {rate_limit} is the budget for all of them together and one busy "
        "client can 429 everyone else. "
        "Set OTM_RATE_LIMIT_DISABLED=1 instead if a gateway in front already limits callers."
    )


def resolve_trusted_proxy(*, environment: str, rate_limit: str | None) -> bool:
    """
    ``OTM_TRUSTED_PROXY``: o operador declara que a API está atrás de um proxy que ele
    controla, e que o endereço de cliente resolvido a partir de ``X-Forwarded-For`` pode
    ser usado para identificar quem chama (rate limit).

    A decisão tem de ser explícita porque a app não consegue verificá-la: o uvicorn reescreve
    ``request.client`` a partir de um cabeçalho controlado pelo cliente **antes** de o nosso
    código correr (`proxy_headers=True` e `forwarded_allow_ips='127.0.0.1'` são os defaults),
    pelo que confiar em silêncio é exatamente o que torna o limite contornável com um cabeçalho.

    Não declarar também não pode ser silencioso, e é aí que esta função deixou de ter um
    default. Desconfiar de um endereço encaminhado obriga a contar esses pedidos num balde
    único; atrás do proxy que `DEPLOYMENT_INVARIANTS.md` torna obrigatório, **todos** os
    pedidos são encaminhados, por isso `120/minute` deixava de ser "120 por chamador" e
    passava a ser "120 para o serviço inteiro" — um chamador esgotava o orçamento de todos os
    outros, sem nada no arranque a dizê-lo. Em `staging`/`production` com o limite ativo, a
    omissão passa a abortar o arranque: um deploy que falha é observável, um serviço que serve
    429 a toda a gente ao fim de duas semanas não é.

    `development` não tem limite por defeito, por isso não há decisão a exigir aí; um limite
    explicitamente configurado em dev também não vê o cabeçalho, e exigir a declaração seria
    burocracia sem risco associado.

    Ver `middleware_rate_limit.client_key` e `docs/architecture/DEPLOYMENT_INVARIANTS.md`.
    """
    declared = _declared_trusted_proxy()
    if declared is not None:
        return declared
    if rate_limit is not None and environment != "development":
        raise _undeclared_trusted_proxy_error(environment=environment, rate_limit=rate_limit)
    return False


def describe_shared_bucket_consequence(
    *,
    environment: str,
    rate_limit: str | None,
    trusted_proxy: bool,
) -> str | None:
    """
    A linha de arranque para quem declarou `OTM_TRUSTED_PROXY=0` com o limite ligado.

    `0` é uma escolha legítima (a app não tem outra chave segura para um chamador que não
    consegue identificar), mas o seu custo — o limite passa a ser um orçamento partilhado —
    não pode ficar por dizer: um 429 vindo do balde partilhado é indistinguível de um 429
    normal do lado do cliente, e sem esta linha o operador só tem "está tudo a dar 429".

    ``None`` quando não há nada a declarar: com proxy de confiança há balde por chamador, sem
    limite não há balde, e em `development` o cabeçalho não chega a aparecer.
    """
    if trusted_proxy or rate_limit is None or environment == "development":
        return None
    return (
        "rate_limit_shared_bucket OTM_TRUSTED_PROXY=off: every request carrying X-Forwarded-For is "
        f"counted in ONE shared bucket, so {rate_limit} is the budget for all forwarded callers "
        "together, not per caller — one busy client can 429 everyone else. Set OTM_TRUSTED_PROXY=1 "
        "if a reverse proxy you control is in front (docs/architecture/DEPLOYMENT_INVARIANTS.md)."
    )


def describe_effective_perimeter(
    *,
    profile: CorsProfile,
    api_key: ApiKeyPerimeter,
    rate_limit: str | None,
    trusted_proxy: bool = False,
) -> str:
    """
    Uma linha que declara o perímetro com que o processo arrancou.

    Sem ela, o log de arranque de um servidor aberto por engano é indistinguível do de um
    servidor protegido: a única diferença observável era o 401 que o operador nunca vê.
    Vai na mensagem (e não em ``extra``) porque o formatador JSON só promove um conjunto
    fixo de campos — ver `observability._JsonFormatter`.

    ``trusted_proxy`` só aparece quando está ligado: é o estado que alarga a superfície
    (passa a aceitar-se um endereço vindo de um cabeçalho) e é por isso o que tem de ser
    legível no arranque. A ausência do marcador é o estado seguro — e o seu custo de
    disponibilidade tem linha própria, ver `describe_shared_bucket_consequence`.
    """
    if api_key.misconfigured:
        key_state = "misconfigured"
    elif api_key.enforced:
        key_state = "enforced"
    else:
        key_state = "off"
    line = (
        "api_perimeter "
        f"environment={profile.environment} "
        f"api_key={key_state} "
        f"rate_limit={rate_limit or 'off'} "
        f"cors_origins={len(profile.origins)}"
    )
    if trusted_proxy:
        line += " trusted_proxy=on"
    return line
