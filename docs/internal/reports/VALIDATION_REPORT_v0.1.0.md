# Relatório de validação — v0.1.0

> **Registo datado — não é o estado corrente do projeto.** Este documento descreve a
> versão que existia quando foi escrito; parte do que afirma já foi corrigido. Ver
> [`docs/internal/README.md`](../README.md) antes de citar qualquer conclusão daqui.


**Ambiente:** Windows 10 (build 26200), PowerShell  
**Data:** 2026-04-01  
**Escopo:** validação manual/automatizada executada na rodada de fechamento; substituir por logs de CI quando aplicável.

## 1. Testes Python

| Comando | Resultado | Notas |
|---------|-----------|-------|
| `python -m pytest` (raiz) | **PASS** | 264 testes, ~1.7s |
| `pytest tests/test_smoke_release_candidate.py tests/test_plot4ai_calibration_fixtures.py tests/test_artifact_import_ai_signals.py tests/test_api.py` | **PASS** | 53 testes (RC + calibração + import AI + API) |

## 2. UI

| Verificação | Resultado |
|-------------|-----------|
| `npm run ci:build:portable` em `apps/web` | **PASS** (typecheck + Vite build) |

## 3. E2E

| Verificação | Resultado |
|-------------|-----------|
| `npm run e2e:smoke` em `apps/web` | **PASS** (1 teste Chromium; fluxo mínimo home → análise → export) |

Nota: `npx playwright install chromium` emitiu aviso de caminho numa invocação separada; o script npm resolveu `@playwright/test` localmente com sucesso.

## 4. CLI (fluxos principais)

| Fluxo | Resultado |
|-------|-----------|
| `otm --version` | **PASS** → `v0.1.0` |
| `otm validate examples/minimal.otm.yaml` | **PASS** |
| `otm analyze … --methodology stride -q` | **PASS** |
| `otm recommend-methodology examples/minimal.otm.yaml` | **PASS** |
| `otm import openapi` (OpenAPI mínimo em temp) `-o` rascunho | **PASS** |
| `otm diff examples/minimal.otm.yaml examples/saas-ordering-v1.otm.yaml --summary-only` | **PASS** |
| `otm backlog analysis.json --format markdown -o ficheiro` | **PASS** (stdout Unicode pode falhar em consola cp1252 — ver limitações) |
| `otm export examples/minimal.otm.yaml -f json` | **PASS** |

Execução via `otm.exe` em `%APPDATA%\Python\Python312\Scripts\` quando `otm` não está no `PATH`.

## 5. API

A suíte `tests/test_api.py` cobre health, OpenAPI, validate, analyze, diff, compare, analyses/diff. Resultado incluído no total **264 passed**.

## 6. Packaging

| Artefacto | Resultado |
|-----------|-----------|
| `python -m build --wheel` | **PASS** → `open_threat_model-0.1.0-py3-none-any.whl` |

## 7. Segredos (verificação básica)

Procura por padrões óbvios de segredos no código não identificou credenciais reais; tokens mencionados em docs/código referem-se a matching lexical (“token-safe”), não a API keys.

## 8. CI remoto

Não executado nesta sessão local. Antes da tag `v0.1.0`, confirmar pipeline(s) no repositório remoto (jobs Python, web, smoke E2E conforme `.github/workflows/` ou equivalente).

## Conclusão da evidência

Todos os itens executados nesta sessão **passaram**. O mantenedor deve ainda confirmar **CI remoto** verde antes da tag final.
