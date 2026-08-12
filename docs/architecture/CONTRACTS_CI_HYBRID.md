# Contratos OpenAPI, gate CI e E2E híbrido

## Superfície OpenAPI fechada (SPA / integrações)

Além de `POST /v1/models/analyze` e `/compare`, os endpoints abaixo expõem `response_model` Pydantic no OpenAPI exportado (`contracts/openapi.json`):

| Método | Caminho | Schema de resposta (JSON) |
|--------|---------|---------------------------|
| POST | `/v1/models/precheck` | `ModelPrecheckResponse` |
| POST | `/v1/models/diff` | `ThreatModelDiff` |
| POST | `/v1/analyses/diff` | `AnalysisDiff` |
| POST | `/v1/remediation/backlog` | `RemediationBacklog` (com `format=json`; `format=markdown` devolve texto) |
| POST | `/v1/exports` | `ExportResponse` |
| POST | `/v1/imports/*` | `ArtifactImportResponse` |

`POST /v1/reports/premium` permanece **sem** modelo JSON único: a resposta é `text/markdown` ou `application/pdf` (documentado no OpenAPI com `response_model=None` e `responses` explícitos).

`ComparisonResultMeta` (resposta de `/compare`) tem **raiz fechada** no Pydantic/OpenAPI; extensões experimentais devem ir para o campo `extensions` (mapa JSON) até serem promovidas a campos tipados.

## Regenerar tipos TypeScript

Na raiz do monorepo:

```bash
python scripts/export_openapi.py
cd apps/web && npm run contracts:generate
```

Ou em `apps/web`: `npm run contracts:sync` (export + generate).

## Gate anti-stale (OpenAPI)

Garante que `contracts/openapi.json` coincide com `app.openapi()` do FastAPI.

```bash
python scripts/verify_openapi_up_to_date.py
```

Em `apps/web`: `npm run contracts:verify`.

O job **CI** `python` executa este passo **antes** de `pytest`. Se falhar, regenerar o OpenAPI e os tipos TS e voltar a commitar.

## Goldens HTTP semânticos (pytest)

Ficheiro de expectativas compactas: `tests/fixtures/golden/http_api_semantic_expectations.json`.

Testes: `tests/test_http_response_goldens.py` — validam forma e campos de alto valor de `POST /v1/models/analyze` e `/compare` (e sanity de precheck / analyses diff), sem snapshot completo da resposta.

## E2E híbrido (UI + API real)

- Configuração: `apps/web/playwright.hybrid.config.ts` — sobe **uvicorn** (`otm_api`) na porta **8000** e **Vite** na **4173** (proxy `/api` → 8000, igual ao `vite.config` de desenvolvimento).
- **Porta da API configurável:** a porta 8000 é muito disputada; se já estiver ocupada, o uvicorn falha no bind e todo o E2E sem mocks fica inexecutável. Defina `OTM_API_PORT` para mover **uvicorn e o proxy do Vite em conjunto** (nunca podem divergir). Para apontar para um backend remoto ou em container, use `OTM_API_URL`, que substitui a origem inteira. Resolução em `apps/web/src/config/devApiTarget.ts` (com testes em `devApiTarget.test.ts`); valores malformados voltam ao default 8000.
- Testes: `apps/web/e2e/hybrid.spec.ts` (sem `page.route` para mocks de API).
- **Pré-checagem:** `npm run e2e:hybrid` chama primeiro `e2e:hybrid:check` → `python ../../scripts/check_hybrid_prereqs.py`. Se falhar, instale a API em modo editável na raiz: `pip install -e ".[dev,cli,api]"`.

```bash
# 1) Raiz do monorepo — ambiente Python com API
pip install -e ".[dev,cli,api]"
python scripts/check_hybrid_prereqs.py

# 2) Web
cd apps/web
npm ci
npx playwright install chromium
npm run e2e:hybrid

# 3) Se a porta 8000 já estiver ocupada
OTM_API_PORT=8123 npm run e2e:hybrid
```

O workflow GitHub Actions **hybrid-e2e** corre estes testes em Ubuntu (Python + Node no mesmo job).

**Requisito:** o `python` invocado pelo npm deve ser o mesmo ambiente onde `otm_api` está instalado (em Windows, evitar misturar Store Python com venv sem o pacote).

## Limitações

- Premium e Markdown de remediação não são “um único schema JSON”; o contrato é por media type.
- E2E híbrido é mais lento que smoke com mocks; mantido como job separado.
