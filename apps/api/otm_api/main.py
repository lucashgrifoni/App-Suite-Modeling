"""
API FastAPI — camada HTTP sobre core, motor, packs e exportadores.

Regras de negócio permanecem em `otm_core_schema`, `otm_threat_engine`, etc.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from otm_threat_engine import ThreatIdCollisionError
from starlette.exceptions import HTTPException as StarletteHTTPException

from otm_api.cors_settings import resolve_cors_profile
from otm_api.document_limits import resolve_max_document_entities
from otm_api.errors import (
    http_exception_handler,
    request_validation_handler,
    threat_id_collision_handler,
)
from otm_api.middleware_api_key import OptionalApiKeyMiddleware
from otm_api.middleware_rate_limit import RateLimitMiddleware, parse_rate_limit
from otm_api.observability import (
    ObservabilityMiddleware,
    register_unhandled_exception_handler,
    setup_api_logging,
)
from otm_api.openapi_security import api_key_header, bearer_token
from otm_api.perimeter_settings import (
    WEAK_API_KEY_WARNING,
    describe_effective_perimeter,
    describe_shared_bucket_consequence,
    has_weak_api_key,
    resolve_api_key_perimeter,
    resolve_rate_limit_default,
    resolve_trusted_proxy,
)
from otm_api.routers import analyses, exports, imports, models, remediation, reports_premium, system, templates

setup_api_logging()
LOG = logging.getLogger("otm.api")

app = FastAPI(
    title="App Suite Modeling API",
    version="0.1.0",
    description=(
        "HTTP API for threat modeling as code: validation, analysis, templates, and exports. "
        "Versioned routes under `/v1`. See `docs/features/API.md` in the repository."
    ),
    openapi_tags=[
        {"name": "System", "description": "Service health."},
        {"name": "Models", "description": "Create, validate, analyze, and compare the canonical document."},
        {"name": "Analyses", "description": "Diff between engine results (`AnalysisResult`)."},
        {"name": "Templates", "description": "Built-in starter templates."},
        {"name": "Export", "description": "JSON, Markdown, Mermaid, and bundles."},
        {
            "name": "Assisted import",
            "description": "Canonical draft from OpenAPI, Terraform, or Kubernetes (no final analysis).",
        },
        {
            "name": "Remediation",
            "description": "Actionable backlog from `AnalysisResult` (heuristic prioritization, not Jira).",
        },
        {
            "name": "Reports",
            "description": "Risk reports in Markdown and PDF.",
        },
    ],
)

app.add_exception_handler(RequestValidationError, request_validation_handler)  # type: ignore[arg-type]
# Substitui o handler de `HTTPException` do FastAPI: serializa os 422 sem morrer num
# surrogate solto e põe o 400 de corpo ilegível no envelope documentado. Ver `errors.py`.
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
# Antes do handler de último recurso: sem isto a recusa por colisão de ids saía como 500.
app.add_exception_handler(ThreatIdCollisionError, threat_id_collision_handler)
register_unhandled_exception_handler(app)

_rate_limit_spec = resolve_rate_limit_default()

_cors = resolve_cors_profile()
_api_key = resolve_api_key_perimeter()
# Aborta o arranque em staging/produção quando o limite está ligado e ninguém declarou se há um
# proxy à frente — ver `resolve_trusted_proxy`. Sem essa declaração, o limite deixa de ser por
# chamador e passa a ser um orçamento único para o serviço inteiro.
_trusted_proxy = resolve_trusted_proxy(environment=_cors.environment, rate_limit=_rate_limit_spec)

# Uma linha, no arranque, a declarar o perímetro efetivo. Sem ela, o log de um servidor
# aberto por engano (chave em branco, ambiente que caiu em `development`, um proxy tratado
# como de confiança) é idêntico ao de um servidor protegido — ver `describe_effective_perimeter`.
_perimeter_line = describe_effective_perimeter(
    profile=_cors,
    api_key=_api_key,
    rate_limit=_rate_limit_spec,
    trusted_proxy=_trusted_proxy,
)
_perimeter_level = logging.WARNING if _api_key.misconfigured else logging.INFO
LOG.log(_perimeter_level, _perimeter_line, extra={"event_name": "api_perimeter"})

# `OTM_TRUSTED_PROXY=0` é uma escolha legítima, mas custa disponibilidade: o limite passa a ser
# um orçamento partilhado por todos os chamadores encaminhados. Do lado do cliente esse 429 é
# indistinguível de qualquer outro, por isso o custo é declarado aqui, a cada arranque.
_shared_bucket_line = describe_shared_bucket_consequence(
    environment=_cors.environment,
    rate_limit=_rate_limit_spec,
    trusted_proxy=_trusted_proxy,
)
if _shared_bucket_line:
    LOG.warning(_shared_bucket_line, extra={"event_name": "rate_limit_shared_bucket"})

# `api_key=enforced` lê-se exatamente igual com 32 bytes aleatórios e com a palavra `x`. Um
# segredo curto é uma escolha legítima e não aborta o arranque (ao contrário de um valor que é
# um interruptor, recusado em `resolve_api_key_perimeter`), mas não pode ficar indistinguível
# de um forte na única evidência que o operador tem.
if has_weak_api_key(_api_key):
    LOG.warning(WEAK_API_KEY_WARNING, extra={"event_name": "api_key_weak"})

# Resolvido no arranque para que uma gralha em `OTM_MAX_DOCUMENT_ENTITIES` aborte o deploy em
# vez de aparecer como um 500 no primeiro pedido com documento — e anunciado quando está
# ligado, porque um 413 num documento legítimo tem de ter uma linha no arranque a explicá-lo.
_entity_ceiling = resolve_max_document_entities()
if _entity_ceiling is not None:
    LOG.info(
        f"document_entity_ceiling max_entities={_entity_ceiling} "
        "(components + data flows + assets per submitted document)",
        extra={"event_name": "document_entity_ceiling"},
    )

# Ordem de registo: o Starlette empilha ao contrário, por isso o **último** registado fica
# por fora. Efetivo (fora -> dentro): Observability -> CORS -> RateLimit -> ApiKey -> rotas.
#
# Três restrições, todas fixadas por testes; qualquer permuta que as satisfaça serve, e esta
# é a única que satisfaz as três:
#
# 1. `RateLimitMiddleware` por **fora** do `OptionalApiKeyMiddleware`. Ao contrário — a ordem
#    original — o 401 da chave de API era devolvido sem chamar `call_next`, por isso o
#    limitador nunca corria e um chamador anónimo tinha um canal **não medido** para `/v1/*`
#    (força bruta da chave, inundação do log de erros, pressão de CPU e de sockets) enquanto
#    só o cliente autenticado era travado. `docs/features/API.md` promete o contrário: o
#    limite aplica-se a *todas* as rotas, contado por chamador. Ver
#    `test_p2r5_api_rate_limit_unauthenticated.py`.
# 2. `ObservabilityMiddleware` por **fora** de tudo. Quando corria por dentro do perímetro, um
#    401 do middleware de chave de API não passava por ele: a rejeição de autenticação — o
#    evento mais relevante para segurança que esta API emite — não aparecia no log estruturado
#    e a resposta saía sem `X-Request-ID`, ao contrário de todos os outros códigos de estado.
#    O mesmo se aplicava ao 429. Ficar por fora **do CORS** (e não logo a seguir) acrescenta o
#    caso que faltava: o 400 "Disallowed CORS origin" de um preflight recusado é respondido
#    pelo `CORSMiddleware` sem chamar `call_next`, por isso era o único estado desta API que
#    não existia no log estruturado — só na linha de acesso do uvicorn, que deixou de ser
#    emitida (ver `observability.setup_api_logging`).
# 3. O `CORSMiddleware` continua por **fora** do perímetro, para que a resposta 401/429 que o
#    browser recebe continue a trazer os cabeçalhos CORS e o cliente consiga lê-la.
app.add_middleware(OptionalApiKeyMiddleware)
if _rate_limit_spec:
    app.add_middleware(
        RateLimitMiddleware,
        limit=parse_rate_limit(_rate_limit_spec),
        trust_forwarded=_trusted_proxy,
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors.origins,
    # Nunca `True` a par de uma origem `*` — ver `cors_settings._credentials_allowed`.
    allow_credentials=_cors.allow_credentials,
    allow_methods=_cors.allow_methods,
    allow_headers=_cors.allow_headers,
)
app.add_middleware(ObservabilityMiddleware)


@app.get(
    "/",
    summary="API entry",
    tags=["System"],
    description="Links to interactive docs and health. Open `/docs` for Swagger UI.",
)
def root() -> dict[str, str]:
    return {
        "service": "App Suite Modeling API",
        "version": app.version,
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "health": "/health",
        "api_v1": "/v1",
    }


app.include_router(system.router)

# As dependências só **documentam** a credencial que `OptionalApiKeyMiddleware` já exige: com
# `auto_error=False` não recusam nada, e o ponto de aplicação continua a ser o middleware. Sem
# elas o contrato não tinha `securitySchemes` nenhum, e o /docs desta API não tinha como
# autenticar-se contra ela. Ver `openapi_security.py`.
v1 = APIRouter(prefix="/v1", dependencies=[Depends(api_key_header), Depends(bearer_token)])
v1.include_router(models.router)
v1.include_router(analyses.router)
v1.include_router(templates.router)
v1.include_router(exports.router)
v1.include_router(imports.router)
v1.include_router(remediation.router)
v1.include_router(reports_premium.router)
app.include_router(v1)
