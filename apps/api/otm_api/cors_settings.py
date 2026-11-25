"""
CORS e perfil de ambiente (`OTM_ENV`, `OTM_CORS_ORIGINS`).

Em `production` sem `OTM_CORS_ORIGINS`, as origens ficam vazias (CORS desativado para browser).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

# Valores aceites, tal como documentados em `docs/architecture/DEPLOYMENT_INVARIANTS.md`.
# Ausente ou vazio = `development` (o default retrocompatível para uso local).
_ENVIRONMENT_BY_VALUE: dict[str, str] = {
    "": "development",
    "development": "development",
    "staging": "staging",
    "prod": "production",
    "production": "production",
}


class InvalidEnvironmentError(ValueError):
    """`OTM_ENV` tem um valor que não corresponde a nenhum perfil documentado."""


class InvalidCorsOriginsError(ValueError):
    """`OTM_CORS_ORIGINS` pede uma configuração que não pode ser servida em segurança."""


# Uma origem `*` não é uma origem: é "qualquer página web da internet".
_WILDCARD_ORIGIN = "*"

# A origem opaca que um browser envia de uma sandbox ou de `file://` (RFC 6454 6.2). Não tem a
# forma `esquema://host`, e listá-la é uma decisão legítima do operador, por isso é aceite por
# nome em vez de cair na recusa por formato.
_OPAQUE_ORIGIN = "null"

# Serialização de origem, tal como o browser a envia no cabeçalho `Origin` e tal como o
# `CORSMiddleware` a compara: `esquema://host[:porta]` e mais nada. Sem caminho, sem barra
# final, sem query, sem fragmento, sem credenciais, sem espaços.
#
# O esquema fica genérico de propósito. Um whitelist de `http`/`https` recusaria origens
# perfeitamente reais que chegam a APIs como esta — `chrome-extension://…`,
# `moz-extension://…`, `capacitor://localhost`, `tauri://localhost` — e trocar um defeito que
# aceita lixo por um que recusa configuração válida não é uma correção. O host aceita a forma
# literal IPv6 (`https://[::1]:8080`) pela mesma razão.
_ORIGIN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9+.\-]*://(\[[0-9A-Fa-f:.]+\]|[^/?#\s:@\[\]]+)(:[0-9]{1,5})?")


@dataclass(frozen=True)
class CorsProfile:
    origins: list[str]
    allow_methods: list[str]
    allow_headers: list[str]
    environment: str
    # Falso quando a lista de origens é (ou inclui) `*`. Ver `_credentials_allowed`.
    allow_credentials: bool = True


def resolve_environment() -> str:
    """
    Perfil de ambiente efetivo, ou erro se `OTM_ENV` não for reconhecido.

    Falhar no arranque é deliberado, pelo mesmo motivo que uma expressão inválida em
    `OTM_RATE_LIMIT` falha (ver `middleware_rate_limit.parse_rate_limit`): antes, qualquer
    valor não previsto — `prd`, `stage`, `prod-eu` — caía em `development`, o que abre o
    CORS a origens de browser com `*` em métodos e cabeçalhos e desliga o rate limit por
    defeito. Uma gralha de um carater desligava dois controlos sem uma linha de aviso, e o
    valor certo não é adivinhável (um `stage` tanto pode querer dizer staging como produção).
    """
    raw_env = (os.environ.get("OTM_ENV") or "").strip().lower()
    environment = _ENVIRONMENT_BY_VALUE.get(raw_env)
    if environment is None:
        accepted = ", ".join(sorted(v for v in _ENVIRONMENT_BY_VALUE if v))
        raise InvalidEnvironmentError(
            f"OTM_ENV={raw_env!r} is not a known environment profile. Accepted values: {accepted} "
            "(unset = development). Refusing to fall back to `development`, which would open CORS "
            "to browser origins and disable the default rate limit."
        )
    return environment


def _refuse_wildcard_origins(environment: str) -> InvalidCorsOriginsError:
    """A recusa de arranque, escrita para quem está a meio de um deploy.

    `OTM_ENV=prd` e `OTM_TRUSTED_PROXY=maybe` já abortam o arranque em vez de degradarem em
    silêncio; `OTM_CORS_ORIGINS=*` era a excepção, e a mais cara delas.
    """
    return InvalidCorsOriginsError(
        f"OTM_CORS_ORIGINS='{_WILDCARD_ORIGIN}' opens /v1/* to every origin on the web, and this is a "
        f"{environment} deployment. docs/architecture/DEPLOYMENT_INVARIANTS.md requires explicit CORS "
        "lists outside development. List the origins that may call this API, comma separated "
        "(OTM_CORS_ORIGINS=https://app.example.com,https://admin.example.com), or unset the variable to "
        "serve no browser origin at all. Refusing to start with a wildcard, which no log line would "
        "have distinguished from a correctly configured server."
    )


def _is_serialized_origin(value: str) -> bool:
    """A entrada tem a forma que o `CORSMiddleware` compara contra o cabeçalho `Origin`."""
    if value in (_WILDCARD_ORIGIN, _OPAQUE_ORIGIN):
        return True
    return bool(_ORIGIN_PATTERN.fullmatch(value))


def _refuse_malformed_origins(malformed: list[str]) -> InvalidCorsOriginsError:
    """A recusa de arranque para uma origem que nenhum browser pode alguma vez igualar.

    Qualquer texto separado por vírgulas era aceite sem verificação de formato, e o custo não
    era teórico: com `OTM_CORS_ORIGINS=https://app.example.com/` — uma barra a mais — o servidor
    responde 200 **sem** `Access-Control-Allow-Origin` (o browser deita a resposta fora) e
    recusa o preflight com 400, enquanto a linha de arranque diz `cors_origins=1`, byte a byte
    igual à de um servidor correto. O preflight recusado nem chega ao log estruturado, porque o
    `CORSMiddleware` responde antes da observabilidade. Uma gralha de um carater punha todos os
    clientes de browser offline e não deixava um único sinal que a distinguisse.

    Recusar no arranque é o tratamento que `OTM_ENV`, `OTM_TRUSTED_PROXY`, `OTM_RATE_LIMIT` e
    `OTM_CORS_ORIGINS=*` já têm. Uma lista com uma entrada boa e uma má é recusada inteira de
    propósito: a alternativa — descartar a má e arrancar — repõe exatamente o servidor
    silenciosamente meio-partido que este erro existe para tornar visível.
    """
    listed = ", ".join(repr(value) for value in malformed)
    return InvalidCorsOriginsError(
        f"OTM_CORS_ORIGINS contains {len(malformed)} entry/entries that no browser can ever match: "
        f"{listed}. An origin is `scheme://host[:port]` and nothing else — no trailing slash, no path, "
        "no query, no spaces (write https://app.example.com, not https://app.example.com/). A value "
        "the browser cannot match is served as a 200 with no Access-Control-Allow-Origin header and a "
        "400 on preflight, which takes every browser client offline while the startup perimeter line "
        "counts it as a working origin. Fix the entry, or unset the variable to serve no browser "
        "origin at all."
    )


def _credentials_allowed(origins: list[str]) -> bool:
    """
    `Access-Control-Allow-Credentials: true` só com uma lista concreta de origens.

    Combinar as duas coisas era uma escalada silenciosa e não o que o operador pediu: com
    `allow_credentials=True`, o `CORSMiddleware` do Starlette **não** emite um `*` literal —
    reflecte a `Origin` de quem chama e junta-lhe `Allow-Credentials: true`. Um `*` literal faz
    o browser recusar leituras cross-origin com credenciais; a reflexão autoriza-as. Escrever
    `*` passava assim a permitir estritamente mais do que escrever `*`.
    """
    return _WILDCARD_ORIGIN not in origins


def resolve_cors_profile() -> CorsProfile:
    environment = resolve_environment()

    raw_origins = (os.environ.get("OTM_CORS_ORIGINS") or "").strip()
    if raw_origins:
        origins = [x.strip() for x in raw_origins.split(",") if x.strip()]
    elif environment == "production":
        origins = []
    else:
        origins = [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]

    if _WILDCARD_ORIGIN in origins and environment != "development":
        raise _refuse_wildcard_origins(environment)

    malformed = [value for value in origins if not _is_serialized_origin(value)]
    if malformed:
        raise _refuse_malformed_origins(malformed)

    if environment == "development":
        methods = ["*"]
        headers = ["*"]
    else:
        methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"]
        # `X-OTM-API-Key` faz parte desta lista porque é o mecanismo de autenticação que a
        # própria API documenta e que o corpo do 401 manda usar. Sem ele, o preflight de
        # qualquer cliente de browser era rejeitado com 400 "Disallowed CORS headers" —
        # exatamente nos ambientes onde `OTM_API_KEY` está realmente definida, e sem aparecer
        # no log (o CORSMiddleware responde antes da observabilidade). Em `development`,
        # `allow_headers=["*"]` escondia o problema.
        headers = ["Content-Type", "Authorization", "X-OTM-API-Key", "X-Request-ID", "Accept"]

    return CorsProfile(
        origins=origins,
        allow_methods=methods,
        allow_headers=headers,
        environment=environment,
        allow_credentials=_credentials_allowed(origins),
    )
