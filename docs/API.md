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
| `POST` | `/v1/models/recommend-methodology` | Sugere engine/metodologia pelo contexto do documento. |
| `POST` | `/v1/models/analyze` | Corre o motor; corpo: `document`, opcional `pack_id`, `methodology`, `auto_recommend_methodology`. |
| `GET` | `/v1/templates` | Lista templates embutidos. |
| `POST` | `/v1/templates/{template_id}/instantiate` | Gera documento a partir do template. |
| `POST` | `/v1/exports` | Gera artefactos (`formats[]`, opcional `analysis`, `pack_id`). |

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

Para `plot4ai`, os blocos seguem subdomínios incrementais como:
- `model_interaction_risks`
- `prompt_input_handling_risks`
- `retrieval_grounding_risks`
- `agent_tool_execution_risks`
- `data_leakage_disclosure_ai`
- `governance_pipeline_risks`

### Formatos de exportação (`POST /v1/exports`)

- `document_json`, `document_markdown`, `flowchart_mermaid`
- `analysis_json`, `analysis_markdown`, `bundle_json` (se `analysis` não for enviado, o motor corre com `pack_id` opcional)

## Erros

- **422** — validação do pedido (FastAPI) ou do documento canónico (`DOCUMENT_VALIDATION_ERROR` + `errors` Pydantic).
- **404** — pack ou template desconhecido (`PACK_NOT_FOUND`, `TEMPLATE_NOT_FOUND`).

## Execução local

```bash
pip install -e ".[api]"
uvicorn otm_api.main:app --reload --port 8000
```

Docker: ver `apps/api/Dockerfile`.
