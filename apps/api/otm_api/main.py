"""
API FastAPI — camada HTTP sobre core, motor, packs e exportadores.

Regras de negócio permanecem em `otm_core_schema`, `otm_threat_engine`, etc.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from otm_api.cors_settings import resolve_cors_profile
from otm_api.errors import request_validation_handler
from otm_api.observability import (
    ObservabilityMiddleware,
    register_unhandled_exception_handler,
    setup_api_logging,
)
from otm_api.routers import analyses, exports, imports, models, remediation, reports_premium, system, templates

setup_api_logging()

app = FastAPI(
    title="App Suite Modeling API",
    version="0.1.0",
    description=(
        "HTTP API for threat modeling as code: validation, analysis, templates, and exports. "
        "Versioned routes under `/v1`. See `docs/API.md` in the repository."
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
register_unhandled_exception_handler(app)

_cors = resolve_cors_profile()
app.add_middleware(ObservabilityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors.origins,
    allow_credentials=True,
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
