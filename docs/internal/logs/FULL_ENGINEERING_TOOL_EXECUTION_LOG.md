# Log de execução de ferramentas — auditoria de conformidade

> **Registo datado — não é o estado corrente do projeto.** Este documento descreve a
> versão que existia quando foi escrito; parte do que afirma já foi corrigido. Ver
> [`docs/internal/README.md`](../README.md) antes de citar qualquer conclusão daqui.


**Data:** 2026-04-06  
**Ambiente:** Windows 10, PowerShell, Python 3.12 (utilizador), repositório local.

Este ficheiro regista apenas o que foi **tentado** nesta auditoria, sem correções ao código.

---

## Resumo

| Ferramenta | Comando (essência) | Resultado | Notas |
|------------|-------------------|-----------|--------|
| Ruff (lint) | `python -m ruff check packages apps tests` | **Sucesso** | Exit 0 |
| Ruff (format check) | `python -m ruff format --check packages apps tests` | **Falha** | 73 ficheiros precisariam reformatação |
| Mypy | `python -m mypy packages/core-schema/otm_core_schema apps/api/otm_api` | **Sucesso** | Alinhado ao CI; âmbito parcial |
| pytest | `python -m pytest -q` | **Sucesso** | 408 passed; 8 DeprecationWarning |
| pytest (smoke RC) | `python -m pytest tests/test_smoke_release_candidate.py -q` | **Sucesso** | 6 passed |
| Boundary script | `python scripts/check_core_adapter_boundary.py` | **Sucesso** | Exit 0 |
| OpenAPI verify | `python scripts/verify_openapi_up_to_date.py` | **Sucesso** | Contrato sincronizado |
| pip-audit | `python -m pip_audit --desc on -S .` | **Sucesso** | “No known vulnerabilities”; aviso de venv/redirect no Windows |
| npm audit (critical) | `npm audit --audit-level=critical` (em `apps/web`) | **Sucesso (gate)** | Exit 0; **5 vulnerabilidades moderadas** reportadas (esbuild/vite cadeia) |
| TypeScript | `npm run typecheck` (em `apps/web`) | **Sucesso** | Exit 0 |
| Vitest | `npm test` (em `apps/web`) | **Sucesso** | 2 ficheiros, 9 testes |
| Gitleaks (git) | `gitleaks detect --source .` | **Sucesso** | 31 commits, no leaks found |
| Gitleaks (no-git) | `gitleaks detect --source . --no-git` | **Ruído** | Falsos positivos em `.venv`/site-packages (não usar sem exclusões) |
| Bandit | `python -m bandit …` | **Não executável** | Módulo `bandit` não instalado; **não configurado no projeto** |
| Semgrep | `semgrep --version` | **Indisponível** | Binário não no PATH; **não configurado no CI** |
| Playwright E2E | `npm run e2e:*` | **Não executado localmente** | Presente no CI; exige `playwright install` e tempo — registado como não verificado nesta sessão |
| npm audit (full moderate) | implícito no output acima | **Informativo** | CI falha só em critical; moderates existem |
| Snyk / SonarQube / Trivy / Checkov | — | **Não configurados / não executados** | Sem ficheiros de workflow ou scripts dedicados no repositório para estes scanners nesta auditoria |

---

## Detalhe por ferramenta

### 1. Ruff check

- **Comando:** `python -m ruff check packages apps tests`
- **Resultado:** sucesso (exit 0).
- **Principais achados:** nenhum erro de lint no conjunto auditado pelo CI.

### 2. Ruff format --check

- **Comando:** `python -m ruff format --check packages apps tests`
- **Resultado:** falha (exit 1).
- **Evidência:** 73 ficheiros “Would reformat”; 187 já formatados.
- **Observação:** o workflow `.github/workflows/github-ci-cd.yml` + `.github/workflows/security-ci-cd.yml` **não** inclui `ruff format --check` — divergência entre “lint limpo” e “formatação canónica”.

### 3. Mypy

- **Comando:** igual ao CI.
- **Resultado:** sucesso em 40 ficheiros no âmbito.
- **Limitação declarada em `pyproject.toml`:** `ignore_missing_imports = true` — enfraquece garantias fora dos stubs.

### 4. pytest

- **Comando:** `python -m pytest -q --tb=no`
- **Resultado:** 408 passed.
- **Warnings:** `DeprecationWarning` relacionado com `HTTP_422_UNPROCESSABLE_ENTITY` vs `HTTP_422_UNPROCESSABLE_CONTENT` (Starlette/FastAPI) em `apps/api/otm_api/routers/_errors.py`, `exports.py`, e stack anyio.

### 5. pip-audit

- **Comando:** `python -m pip_audit --desc on -S .`
- **Resultado:** nenhuma CVE/OSV conhecida no ambiente analisado.
- **Nota:** aviso de localização de venv no Windows (redirect/junction); não invalida o resultado funcional.

### 6. npm audit (apps/web)

- **Comando:** `npm audit --audit-level=critical`
- **Resultado:** exit 0 (gate critical).
- **Conteúdo:** 5 vulnerabilidades **moderadas** — cadeia `esbuild` / `vite` / `vitest` (GHSA-67mh-4wv8-2f99 — contexto típico de **servidor de desenvolvimento**).

### 7. Vitest + tsc

- **Vitest:** 9 testes em 2 ficheiros (`localePolicy`, `exportArtifactLocale`).
- **Typecheck:** sem erros.

### 8. Gitleaks

- **Modo git:** limpo nos commits analisados.
- **Modo --no-git sem exclusão de `.venv`:** inutilizável sem `.gitleaksignore` ou path scope — **gap de maturidade** para scans ad-hoc em estações de trabalho com venv dentro do tree.

### 9. Ferramentas ausentes ou não integradas

| Ferramenta | Estado |
|------------|--------|
| Bandit | Não em `pyproject.toml` [dev]; não no CI |
| Semgrep | Não no CI; não disponível no PATH da sessão |
| detect-secrets / pre-commit hooks | Não identificados como padrão obrigatório no repo |
| Trivy (imagem Docker) | Não executado; Dockerfile existe mas sem scan no workflow analisado |
| Checkov (IaC) | `docker-compose.yml` existe; sem pipeline Checkov |

---

## Conclusão do log

As ferramentas **alinhadas ao CI atual** (ruff check, mypy parcial, pip-audit, pytest, npm audit critical, verificação OpenAPI, script de boundary) foram executadas com sucesso, exceto **ruff format --check**, que **falharia** se fosse adicionado como gate sem reformatação prévia.

Ferramentas SAST adicionais (Bandit, Semgrep) e scans de contentor/IaC **não fazem parte do pipeline observado** e não foram executadas com sucesso end-to-end nesta auditoria.
