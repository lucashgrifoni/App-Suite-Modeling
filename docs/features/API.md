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

Contrato exportado, gate anti-stale, goldens HTTP e E2E híbrido: ver **`docs/architecture/CONTRACTS_CI_HYBRID.md`**.

## Perímetro opcional (API key e rate limit)

| Variável | Efeito |
|----------|--------|
| `OTM_API_KEY` | Se definida (não vazia), todos os pedidos a **`/v1/*`** exigem **`X-OTM-API-Key: <valor>`** ou **`Authorization: Bearer <valor>`**. Rotas como `/health`, `/docs`, `/openapi.json` permanecem sem chave. |
| `OTM_RATE_LIMIT` | Expressão no formato [`limits`](https://limits.readthedocs.io/) (ex.: `120/minute`). Se definida, aplica-se como limite global a **todas** as rotas, incluindo `/health` e `/v1/*`, contado por chamador (ver `OTM_TRUSTED_PROXY`). Uma expressão malformada — ou `0/...`, que não aceitaria pedido nenhum — faz a app falhar no arranque, em vez de desactivar (ou trancar) o controlo em silêncio. O contador é em memória do processo: com vários workers o limite é por worker. |
| `OTM_RATE_LIMIT_DISABLED` | `1` / `true` — desativa o rate limit mesmo em staging/produção. |
| `OTM_TRUSTED_PROXY` | `1` / `true` — declara que a API está atrás de um reverse proxy do operador, e só então o endereço resolvido de `X-Forwarded-For` conta como identidade do chamador. Por omissão, pedidos com esse cabeçalho partilham um único balde de rate limit (o limite continua a valer, mas não pode ser reiniciado a rodar o cabeçalho). **Requer flags específicas do uvicorn** — ver `docs/architecture/DEPLOYMENT_INVARIANTS.md`. |
| (sem `OTM_RATE_LIMIT` e sem `OTM_RATE_LIMIT_DISABLED`) | Em **`development`** (defeito de `OTM_ENV`): sem limite. Em **staging** / **production**: limite por defeito **`120/minute`**. |

Sem `OTM_API_KEY`, o comportamento permanece o de API aberta na rede onde estiver exposta — ver **`docs/architecture/DEPLOYMENT_INVARIANTS.md`**.

Em `staging`/`production`, os cabeçalhos aceites em CORS são explícitos e incluem `X-OTM-API-Key`, para que um cliente de browser possa autenticar-se com o mecanismo que esta API documenta.

## Endpoints (MVP)

| Método | Caminho | Descrição |
|--------|---------|-----------|
| `GET` | `/health` | Liveness. |
| `POST` | `/v1/models` | Cria modelo mínimo válido (corpo vazio). |
| `POST` | `/v1/models/validate` | Valida `document` JSON. |
| `POST` | `/v1/models/precheck` | Pré-check de completude (`score_0_100`, `methodology_fit_matrix`, …) + `methodology_completeness`; corpo: `document`, opcional `methodology`. Não executa heurísticas STRIDE. |
| `POST` | `/v1/models/diff` | Compara duas raízes canónicas: corpo `{ "baseline": {...}, "revised": {...} }` (mesmo formato que `document`). Devolve **apenas** `ThreatModelDiff` JSON (contrato estável). |
| `POST` | `/v1/models/compare` | Comparação semântica completa: mesmo par de documentos + opcional `run_analysis`, `pack_id`, ou **par** `baseline_analysis` / `revised_analysis` (ambos ou nenhum). Resposta: `ThreatModelComparisonResult` (estrutura + agregados + insights + deltas). |
| `POST` | `/v1/analyses/diff` | Corpo `{ "baseline_analysis": {...}, "revised_analysis": {...} }` (dois `AnalysisResult`). Devolve `AnalysisDiff`. |
| `POST` | `/v1/models/recommend-methodology` | Sugere engine/metodologia pelo contexto do documento. |
| `POST` | `/v1/models/analyze` | Corre o motor; corpo: `document`, opcional `pack_id`, `methodology`, `auto_recommend_methodology`. |
| `GET` | `/v1/templates` | Lista templates embutidos. Query opcional: `category`, `tag`, `complexity`, `q`. |
| `GET` | `/v1/templates/{template_id}` | Metadados de um template (manifest). |
| `POST` | `/v1/templates/{template_id}/instantiate` | Gera documento a partir do template. |
| `POST` | `/v1/exports` | Gera artefactos (`formats[]`, opcional `analysis`, `pack_id`). |
| `POST` | `/v1/imports/openapi` | `multipart/form-data` campo `file` (OpenAPI/Swagger YAML/JSON). Resposta: rascunho canónico + `inferences` / `unknowns` / `assumptions` (não é análise). |
| `POST` | `/v1/imports/terraform` | Um ficheiro `.tf`. |
| `POST` | `/v1/imports/kubernetes` | YAML multi-manifests. |
| `POST` | `/v1/remediation/backlog` | Corpo: `document` + `analysis` **ou** `run_analysis: true`. Query: `format` = json (default) ou markdown; `group_by` opcional. Ver `docs/features/REMEDIATION_BACKLOG.md`. |
| `POST` | `/v1/reports/premium` | Report premium: `document`, `analysis` ou `run_analysis`, opcional `baseline_analysis`, `level` (executive/standard/deep), `output_format` (markdown/pdf). Ver `docs/features/PREMIUM_REPORTS.md`. |

Ver também `docs/features/ARTIFACT_IMPORT.md`.

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
| `ANALYSIS_DOCUMENT_MISMATCH` | 422 | A análise enviada não foi produzida para o documento enviado ao lado dela. Em `/v1/models/compare` aplica-se a cada par (`baseline`+`baseline_analysis`, `revised`+`revised_analysis`), e o `loc` de cada erro nomeia o campo em falta. Exceção deliberada: `baseline_analysis` em `/v1/reports/premium`, que é de outra versão por definição. |
| `REMEDIATION_GROUP_BY_INVALID` | 422 | `group_by` fora de `root-cause` \| `control` \| `category`. Antes, um valor desconhecido devolvia 200 com o agrupamento por defeito. |
| `REMEDIATION_INPUT` | 400 | Nem `analysis` nem `run_analysis: true` em `/v1/remediation/backlog`. |
| `IMPORT_EMPTY_ARTIFACT` | 400 | Upload de zero bytes em `/v1/imports/*`. |
| `IMPORT_NOT_UTF8` | 400 | O artefacto não é texto UTF-8. |
| `IMPORT_ARTIFACT_INVALID` | 400 | O artefacto é texto mas não tem a forma esperada. |
| `TEMPLATE_INVALID` | 422 | Template existe mas o YAML não valida como documento canónico. |
| `PACK_NOT_FOUND` | 404 | `pack_id` desconhecido. |
| `TEMPLATE_NOT_FOUND` | 404 | `template_id` desconhecido. |

Exceção conhecida ao envelope: o **413** de upload acima do limite em `/v1/imports/*` ainda
devolve `detail` como string (`"Artifact exceeds 2 MiB limit (MVP)."`), sem código estável. Um
cliente que leia `detail["code"]` tem de tratar o 413 pelo status até isso ser corrigido.

Respostas emitidas por middleware **não** passam por `detail`: trazem `{code, message}` na raiz,
como a validação de envelope do pedido. São o **401** (`API_KEY_REQUIRED`,
`API_KEY_MISCONFIGURED`), o **429** (`RATE_LIMITED`) e o **500** (`INTERNAL_ERROR`, com
`request_id`).

Implementação: `apps/api/otm_api/routers/_errors.py` e `apps/api/otm_api/errors.py`.

## Execução local

```bash
pip install -e ".[api]"
uvicorn otm_api.main:app --reload --port 8000
```

Docker: ver `apps/api/Dockerfile`.
