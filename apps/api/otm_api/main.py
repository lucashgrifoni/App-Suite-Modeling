"""
API FastAPI — camada HTTP sobre core, motor, packs e exportadores.

Regras de negócio permanecem em `otm_core_schema`, `otm_threat_engine`, etc.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

from otm_api.cors_settings import resolve_cors_profile
from otm_api.errors import http_exception_handler, request_validation_handler
from otm_api.middleware_api_key import OptionalApiKeyMiddleware
from otm_api.middleware_rate_limit import RateLimitMiddleware, parse_rate_limit
from otm_api.observability import (
    ObservabilityMiddleware,
    register_unhandled_exception_handler,
    setup_api_logging,
)
from otm_api.perimeter_settings import (
    describe_effective_perimeter,
    describe_shared_bucket_consequence,
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
            "description": "Premium executive/standard/deep reports (Markdown and PDF).",
        },
    ],
)

app.add_exception_handler(RequestValidationError, request_validation_handler)  # type: ignore[arg-type]
# Substitui o handler de `HTTPException` do FastAPI: serializa os 422 sem morrer num
# surrogate solto e põe o 400 de corpo ilegível no envelope documentado. Ver `errors.py`.
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
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

# Ordem de registo: o Starlette empilha ao contrário, por isso o **último** registado fica
# por fora. Efetivo (fora -> dentro): CORS -> Observability -> ApiKey -> RateLimit -> rotas.
#
# `ObservabilityMiddleware` tem de ficar por fora do perímetro: quando corria por dentro,
# um 401 do middleware de chave de API não passava por ele, ou seja, a rejeição de
# autenticação — o evento mais relevante para segurança que esta API emite — não aparecia
# no log estruturado e a resposta saía sem `X-Request-ID`, ao contrário de todos os outros
# códigos de estado. O mesmo se aplicava ao 429 do rate limit.
if _rate_limit_spec:
    app.add_middleware(
        RateLimitMiddleware,
        limit=parse_rate_limit(_rate_limit_spec),
        trust_forwarded=_trusted_proxy,
    )
app.add_middleware(OptionalApiKeyMiddleware)
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors.origins,
    # Nunca `True` a par de uma origem `*` — ver `cors_settings._credentials_allowed`.
    allow_credentials=_cors.allow_credentials,
    allow_methods=_cors.allow_methods,
    allow_headers=_cors.allow_headers,
)


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

v1 = APIRouter(prefix="/v1")
v1.include_router(models.router)
v1.include_router(analyses.router)
v1.include_router(templates.router)
v1.include_router(exports.router)
v1.include_router(imports.router)
v1.include_router(remediation.router)
v1.include_router(reports_premium.router)
app.include_router(v1)
