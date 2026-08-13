"""
CORS e perfil de ambiente (`OTM_ENV`, `OTM_CORS_ORIGINS`).

Em `production` sem `OTM_CORS_ORIGINS`, as origens ficam vazias (CORS desativado para browser).
"""

from __future__ import annotations

import os
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
