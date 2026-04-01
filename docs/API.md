# API HTTP (FastAPI)

## Arquitetura

| Camada | Pacote / módulo | Responsabilidade |
|--------|-----------------|------------------|
| HTTP | `otm_api.routers.*` | Rotas, status codes, `HTTPException` com `detail` estruturado. |
| Contratos | `otm_api.schemas.*` | Corpos e respostas Pydantic (OpenAPI). |
| Domínio fino | `otm_api.domain.*` | Enums e tipos sem dependência de FastAPI. |
| Orquestração | `otm_api.services.*` | Chama `otm_core_schema`, `otm_threat_engine`, `otm_industry_packs`, `otm_exporters`. |
| Erros | `otm_api.errors` | Formato comum para validação de pedido (`RequestValidationError`). |

A lógica de threat modeling **não** vive na API: validação e modelo em `otm_core_schema`, análise em `otm_threat_engine`, templates/packs em `otm_industry_packs`, artefactos em `otm_exporters`.

## Base URL e versão

- Rotas de negócio: **`/v1/...`**
- Saúde: **`/health`** (sem prefixo, para probes)

Documentação interativa: **`/docs`** (Swagger UI), **`/redoc`**.

## Endpoints (MVP)

| Método | Caminho | Descrição |
|--------|---------|-----------|
| `GET` | `/health` | Liveness. |
| `POST` | `/v1/models` | Cria modelo mínimo válido (corpo vazio). |
| `POST` | `/v1/models/validate` | Valida `document` JSON. |
| `POST` | `/v1/models/diff` | Compara duas raízes canónicas: corpo `{ "baseline": {...}, "revised": {...} }` (mesmo formato que `document`). Devolve **apenas** `ThreatModelDiff` JSON (contrato estável). |
| `POST` | `/v1/models/compare` | Comparação semântica completa: mesmo par de documentos + opcional `run_analysis`, `pack_id`, ou **par** `baseline_analysis` / `revised_analysis` (ambos ou nenhum). Resposta: `ThreatModelComparisonResult` (estrutura + agregados + insights + deltas). |
| `POST` | `/v1/analyses/diff` | Corpo `{ "baseline_analysis": {...}, "revised_analysis": {...} }` (dois `AnalysisResult`). Devolve `AnalysisDiff`. |
| `POST` | `/v1/models/recommend-methodology` | Sugere engine/metodologia pelo contexto do documento. |
| `POST` | `/v1/models/analyze` | Corre o motor; corpo: `document`, opcional `pack_id`, `methodology`, `auto_recommend_methodology`. |
| `GET` | `/v1/templates` | Lista templates embutidos. |
| `POST` | `/v1/templates/{template_id}/instantiate` | Gera documento a partir do template. |
| `POST` | `/v1/exports` | Gera artefactos (`formats[]`, opcional `analysis`, `pack_id`). |
| `POST` | `/v1/imports/openapi` | `multipart/form-data` campo `file` (OpenAPI/Swagger YAML/JSON). Resposta: rascunho canónico + `inferences` / `unknowns` / `assumptions` (não é análise). |
| `POST` | `/v1/imports/terraform` | Um ficheiro `.tf`. |
| `POST` | `/v1/imports/kubernetes` | YAML multi-manifests. |
| `POST` | `/v1/remediation/backlog` | Corpo: `document` + `analysis` **ou** `run_analysis: true`. Query: `format` = json (default) ou markdown; `group_by` opcional. Ver `docs/REMEDIATION_BACKLOG.md`. |

Ver também `docs/ARTIFACT_IMPORT.md`.

## Exemplos por metodologia (`POST /v1/models/analyze`)

```json
{
  "document": { "...": "..." },
  "methodology": "stride"
}
```

```json
{
  "document": { "...": "..." },
  "methodology": "linddun"
}
```

```json
{
  "document": { "...": "..." },
  "methodology": "nist_data_centric"
}
```

```json
{
  "document": { "...": "..." },
  "methodology": "octave_allegro"
}
```

```json
{
  "document": { "...": "..." },
  "methodology": "cia_die"
}
```

```json
{
  "document": { "...": "..." },
  "methodology": "pasta"
}
```

```json
{
  "document": { "...": "..." },
  "methodology": "plot4ai"
}
```

Exemplo de recomendação automática:

```json
{
  "document": { "...": "..." },
  "auto_recommend_methodology": true
}
```

### Exemplo de saída especializada (PASTA/PLOT4ai)

`POST /v1/models/analyze` agora pode incluir `methodology_insights` (blocos estruturados e opcionais), mantendo o contrato principal:

```json
{
  "methodology": "pasta",
  "methodology_insights": {
    "profile": "PASTA advanced / risk-centric",
    "blocks": [
      { "key": "attack_surface", "title": "Attack surface", "items": ["api-gateway->orders-api"] },
      { "key": "risk_oriented_findings", "title": "Risk-oriented findings", "items": ["..."] }
    ]
  }
}
```

Para `plot4ai`, `methodology_insights.blocks` usa chaves de **camada** (ex.: `model_interaction_layer`, `prompt_input_layer`, `retrieval_grounding_layer`, `vector_embedding_layer`, `agent_tool_layer`, `provider_integration_layer`, `governance_observability_layer`). O campo **`ai_system_context`** agrega `synopsis`, `pattern_tags`, `layers`, superfícies de risco, recomendações e `heuristic_ids_by_layer` (agrupamento `plot4ai_*`). Ver [PLOT4AI_AI_SYSTEM.md](PLOT4AI_AI_SYSTEM.md).

### Formatos de exportação (`POST /v1/exports`)

- `document_json`, `document_markdown`, `flowchart_mermaid`
- `analysis_json`, `analysis_markdown`, `bundle_json` (se `analysis` não for enviado, o motor corre com `pack_id` opcional)

## Erros

Há **dois formatos** de corpo JSON em erro (ver [CONTRACT_AND_SNAPSHOTS.md](CONTRACT_AND_SNAPSHOTS.md)):

1. **Rotas de negócio (`HTTPException`):** chave **`detail`** com objeto `{ "code", "message" }` ou, em 422 com validação interna, `{ "code", "message", "errors" }`.
2. **Validação de envelope do pedido (`RequestValidationError`):** corpo **sem** `detail`, com `{ "code": "REQUEST_VALIDATION_ERROR", "message", "status", "errors" }`.

Códigos estáveis usados nas rotas (sempre dentro de `detail`):

| Código | HTTP | Situação |
|--------|------|----------|
| `DOCUMENT_VALIDATION_ERROR` | 422 | `document` inválido para o schema canónico. |
| `ANALYSIS_VALIDATION_ERROR` | 422 | Campo `analysis` não é um `AnalysisResult` válido. |
| `TEMPLATE_INVALID` | 422 | Template existe mas o YAML não valida como documento canónico. |
| `PACK_NOT_FOUND` | 404 | `pack_id` desconhecido. |
| `TEMPLATE_NOT_FOUND` | 404 | `template_id` desconhecido. |

Implementação: `apps/api/otm_api/routers/_errors.py` e `apps/api/otm_api/errors.py`.

## Execução local

```bash
pip install -e ".[api]"
uvicorn otm_api.main:app --reload --port 8000
```

Docker: ver `apps/api/Dockerfile`.
