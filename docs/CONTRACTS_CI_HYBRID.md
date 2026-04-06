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
- Testes: `apps/web/e2e/hybrid.spec.ts` (sem `page.route` para mocks de API).

```bash
# Raiz: ambiente com pip install -e ".[api]"
cd apps/web
npm ci
npx playwright install chromium
npm run e2e:hybrid
```

O workflow GitHub Actions **hybrid-e2e** corre estes testes em Ubuntu.

**Requisito:** Python no PATH com `otm_api` instalado; em Windows o mesmo comando funciona se `python` apontar para esse ambiente.

## Limitações

- Premium e Markdown de remediação não são “um único schema JSON”; o contrato é por media type.
- E2E híbrido é mais lento que smoke com mocks; mantido como job separado.
