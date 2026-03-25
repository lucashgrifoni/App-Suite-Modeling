"""
API FastAPI — camada HTTP sobre core, motor, packs e exportadores.

Regras de negócio permanecem em `otm_core_schema`, `otm_threat_engine`, etc.
"""

from __future__ import annotations

from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from otm_api.errors import request_validation_handler
from otm_api.routers import analyses, exports, imports, models, remediation, system, templates

app = FastAPI(
    title="App Suite Modeling API",
    version="0.2.0",
    description=(
        "Exposição HTTP do threat modeling as code: validação, análise, templates e exportação. "
        "Rotas versionadas em `/v1`. Ver `docs/API.md` no repositório."
    ),
    openapi_tags=[
        {"name": "Sistema", "description": "Saúde do serviço."},
        {"name": "Modelos", "description": "Criação, validação, análise e comparação do documento canónico."},
        {"name": "Análises", "description": "Diff entre resultados de motor (`AnalysisResult`)."},
        {"name": "Templates", "description": "Modelos iniciais embutidos."},
        {"name": "Exportação", "description": "JSON, Markdown, Mermaid e bundles."},
        {
            "name": "Importação assistida",
            "description": "Rascunho canónico a partir de OpenAPI, Terraform ou Kubernetes (sem análise final).",
        },
        {
            "name": "Remediação",
            "description": "Backlog acionável a partir de `AnalysisResult` (priorização heurística, não Jira).",
        },
    ],
)

app.add_exception_handler(RequestValidationError, request_validation_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(system.router)

v1 = APIRouter(prefix="/v1")
v1.include_router(models.router)
v1.include_router(analyses.router)
v1.include_router(templates.router)
v1.include_router(exports.router)
v1.include_router(imports.router)
v1.include_router(remediation.router)
app.include_router(v1)
