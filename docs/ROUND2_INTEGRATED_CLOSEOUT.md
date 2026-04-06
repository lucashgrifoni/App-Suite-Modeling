# Rodada 2 — fecho integrado (OpenAPI/TS, diff 1.3, anti-patterns estruturais, import Python)

## Contratos

- Export: `python scripts/export_openapi.py` → `contracts/openapi.json`.
- SPA: `cd apps/web && npm run contracts:sync` (export + `openapi-typescript`).
- Endpoints `analyze` e `compare` com `response_model` Pydantic no FastAPI.

## Diff semântico

- Versão **1.3**: `semantic_interpretation_links` (lista correlacional ref → secção).
- `comparison_contract_version`: **1.3**.

## Anti-patterns

- Flag `structural_primary` no catálogo + ramo no motor; prioridade para sinais de grafo nos perfis admin, upload, API, e-commerce.

## Repo scan

- Ficheiros `.py`; inferências `python_web_framework` / `python_asgi_server`; campo `detected_stacks`.

## E2E

- `npm run e2e:critical` inclui `import.spec.ts` e jornadas enriquecidas com meta 1.3.

## Limitações

- Ver secção “Limitações” em `audit-gpt.md`.
