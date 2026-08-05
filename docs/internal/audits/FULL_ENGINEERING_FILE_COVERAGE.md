# Cobertura da auditoria por área do repositório

> **Registo datado — não é o estado corrente do projeto.** Este documento descreve a
> versão que existia quando foi escrito; parte do que afirma já foi corrigido. Ver
> [`docs/internal/README.md`](../README.md) antes de citar qualquer conclusão daqui.


**Data:** 2026-04-06  
**Legenda de status:** ok | atenção | crítico | não verificável

“Auditado” significa: revisão de estrutura, amostragem de ficheiros representativos, grep direcionado a riscos, e/ou execução de ferramenta global quando aplicável — **não** linha-a-linha de todos os 600+ ficheiros.

---

| Área | Auditado | Tipo de análise | Status | Resumo |
|------|----------|-----------------|--------|--------|
| `packages/core-schema/` | Sim | Mypy (CI scope), boundary, amostragem `document.py`, testes | ok | Coração do contrato; bem testado. |
| `packages/threat-engine/` | Sim | Amostragem `engine.py`, grep rate limit/auth, testes existentes | atenção | Motor grande; coberto por testes mas complexidade elevada. |
| `packages/exporters/` | Sim | Indireto via testes `test_exporters.py`, estrutura | ok | |
| `packages/explainability/` | Sim | Indireto via testes de contrato | ok | |
| `packages/framework-mappings/` | Sim | Indireto via testes | ok | |
| `packages/diagram-engine/` | Sim | Indireto via testes / UI | ok | |
| `packages/industry-packs/` | Sim | Dados YAML/JSON + `registry_data.py` (E501 ignorado) | atenção | Ficheiros de dados enormes; manutenção cognitiva alta. |
| `packages/artifact-import/` | Sim | `imports.py` API + grep subprocess; testes dedicados | ok | Import com limite de bytes. |
| `packages/report-premium/` | Sim | Indireto via testes premium / i18n | ok | |
| `apps/api/` | Sim | `main.py`, CORS, observability, routers imports, Dockerfile, grep auth | atenção | Sem auth/rate limit; logging prudente. |
| `apps/cli/` | Sim | Estrutura Typer, amostragem comandos, subprocess em scripts | ok | |
| `apps/web/` | Sim | `package.json`, `vite.config.ts`, grep CSP/storage/XSS, Vitest, tsc | atenção | Poucos unit tests TS; proxy dev para API. |
| `tests/` | Sim | pytest completo (408) | ok | Forte cobertura de domínio e contratos. |
| `scripts/` | Sim | `dev_env.py` (shell=True Win), boundary, openapi, grep subprocess | atenção | Dev-only patterns aceitáveis com ressalvas. |
| `contracts/` | Sim | `verify_openapi_up_to_date.py` | ok | Sincronizado com código. |
| `examples/` | Parcial | Listagem + papel no produto | ok | Dados de exemplo; risco baixo. |
| `fixtures/` (se existir como tal) | Indireto | Via testes | ok | |
| `docs/` | Sim | Amostragem ARCHITECTURE, KNOWN_LIMITATIONS, índice | ok | Volume alto; consistente com código em pontos críticos. |
| `.github/workflows/` | Sim | `ci.yml`, dependabot | ok | Bom leque de jobs; sem SAST extra. |
| `apps/api/Dockerfile` | Sim | Leitura | ok | Non-root user. |
| `docker-compose.yml` | Sim | Existência | não verificável | Não validado com compose up nesta auditoria. |
| `gitpage/` | Parcial | Estrutura Vite/marketing | não verificável | Fora do núcleo do produto; não executado build/test nesta sessão. |
| `.cursor/` / regras IDE | Excluído | — | não verificável | Artefactos de ferramenta; impacto indireto em qualidade. |
| `artifacts/` | N/A | `.gitignore` | ok | Esperado ignorado. |
| `.venv/` / `node_modules/` | Não auditado (código) | — | não verificável | Dependências instaladas; gitleaks --no-git polui com FP. |

---

## Áreas com cobertura limitada (honestidade)

1. **Cada ficheiro Python/TS** — não lido integralmente; risco residual de issues pontuais não grepáveis.
2. **Playwright E2E** — workflows CI descritos; **execução local não repetida** nesta auditoria → confiança derivada do pipeline.
3. **`gitpage/`** — site estático separado; não correlacionado ao threat engine.
4. **Runtime container** — não executado `docker build` / Trivy nesta sessão.

---

## Mapa rápido de entradas do sistema

| Entrada | Localização |
|---------|-------------|
| API HTTP | `uvicorn otm_api.main:app` — `apps/api/otm_api/main.py` |
| CLI | `otm` → `otm_cli.main:main` |
| Web SPA | Vite `apps/web` |
| Contrato | `contracts/openapi.json` + `scripts/export_openapi.py` |

---

*Este mapa deve ser atualizado se novas apps ou pacotes forem adicionados na raiz do monorepo.*
