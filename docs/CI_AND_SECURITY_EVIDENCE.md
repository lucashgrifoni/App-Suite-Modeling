# Evidência consolidada — CI, tipagem, SCA, CLI, observabilidade e perímetro da API

Documento único que substitui relatórios de execução dispersos (rodada de higiene docs, 2026-04).  
**Índice:** [Ruff + Bandit](#0-ruff-lint--formato) · [Mypy](#1-mypy-no-ci-monorepo) · [SCA](#2-sca-supply-chain) · [CLI modular](#3-refatoração-da-cli) · [Observabilidade](#4-observabilidade-da-api) · [Perímetro / CORS](#5-endurecimento-de-perímetro-da-api) · [Semgrep](#6-semgrep) · [Trivy](#7-trivy-imagem-api)

---

## 0. Ruff (lint + formato)

### Comandos no CI (job `python`)

```bash
ruff check packages apps tests
ruff format --check packages apps tests
```

### Critérios de aceite

- **Lint:** regras em `[tool.ruff.lint]` no `pyproject.toml` (`E`, `F`, `I`, `UP`), com `per-file-ignores` onde documentado.
- **Formato:** o repositório mantém estilo canónico Ruff; PRs que desviarem falham no job `Ruff (format)`.

### Local

```bash
ruff check packages apps tests
ruff format packages apps tests
```

### Bandit (SAST, Python)

- Job `python`: `python -m bandit -r packages apps -ll -q` (severidade **medium** e acima; `-q` reduz ruído).
- Dependência: `bandit>=1.7` no extra `[dev]` do `pyproject.toml` (instalado com `pip install -e ".[dev,cli,api]"` no CI).

---

## 1. Mypy no CI (monorepo)

### Pacotes cobertos (job `python`)

O comando no `.github/workflows/ci.yml` inclui **todos** os pacotes Python de primeira linha e a CLI:

- `packages/core-schema/otm_core_schema`
- `apps/api/otm_api`
- `packages/explainability/otm_explainability`
- `packages/framework-mappings/otm_framework_mappings`
- `packages/diagram-engine/otm_diagram_engine`
- `apps/cli/otm_cli`
- `packages/exporters/otm_exporters`
- `packages/artifact-import/otm_artifact_import`
- `packages/report-premium/otm_report_premium`
- `packages/threat-engine/otm_threat_engine`
- `packages/industry-packs/otm_industry_packs`

### Strictness

- Configuração global em `[tool.mypy]` no `pyproject.toml` (`python_version`, `warn_unused_ignores`, `show_error_codes`).
- `ignore_missing_imports = true` no global; próximo passo de maturidade: `[[tool.mypy.overrides]]` por pacote e stubs onde fizer sentido.

### Critérios de aceite

- Job `Mypy (monorepo)` falha em erros de tipo nos diretórios listados.

---

## 2. SCA (supply chain)

### Ferramentas

| Stack | Ferramenta | Onde |
|-------|------------|------|
| Python | **pip-audit** (OSV/PyPI) | Job `python` no CI, após `pip install -e ".[dev,cli,api]"` |
| Node | **npm audit** | Job `web`, `apps/web`, após `npm ci` |

### Thresholds

- **Python:** `python -m pip_audit --desc on -S .` — gate estrito (qualquer vulnerabilidade conhecida falha o CI na árvore resolvida).
- **Node:** `npm audit --audit-level=critical` e **`npm audit --audit-level=moderate`** (job `web`; após upgrade Vite 6 / Vitest 3 a árvore `apps/web` ficou sem CVEs reportados na resolução actual).

### Política de exceção

Não silenciar findings sem registo (issue/ADR com CVE, plano e prazo). Preferir upgrade de dependência.

### Dependabot

- `.github/dependabot.yml`: atualizações semanais para **pip** (raiz) e **npm** (`apps/web`).

---

## 3. Refatoração da CLI

### Problema resolvido

`apps/cli/otm_cli/cli.py` era um god module monolítico; hoje é **bootstrap** (~70 linhas) com comandos em `commands/` e orquestração em `application/`.

### Estrutura

```
apps/cli/otm_cli/
  cli.py          # Typer + registo de comandos
  main.py
  commands/
  application/
  shared/
```

### Testabilidade

- `tests/test_cli_application.py` cobre serviços sem Typer.
- `tests/test_cli.py` e smoke mantêm contrato externo.

---

## 4. Observabilidade da API

### Implementação

1. **`otm_api.observability`**
   - `setup_api_logging()`: JSON por linha em stdout.
   - `ObservabilityMiddleware`: `request_id` (`X-Request-ID`), duração, sucesso/falha.
   - `register_unhandled_exception_handler`: resposta JSON genérica com `request_id`, sem stack ao cliente.

2. **`main.py`**: logging antes da app; middleware de observabilidade na stack (coordenado com CORS).

### Campos típicos de log HTTP

`request_id`, `method`, `path`, `status_code`, `duration_ms`, `event_name` (`http_request_completed` \| `http_request_failed` \| `unhandled_route_exception`).

Variável: `OTM_LOG_LEVEL` (default `INFO`).

### O que não é logado

- Corpo de pedidos, payloads OTM/análise completos, secrets.

---

## 5. Endurecimento de perímetro da API

### Decisão

**Cenário A (local / internal-only):** API **sem** authn/authz de aplicação no código; deployment em rede confiável ou gateway. **CORS e perfis** parametrizados para produção não herdar defaults de desenvolvimento.

### Implementação

- `otm_api.cors_settings.resolve_cors_profile()`: `OTM_ENV`, `OTM_CORS_ORIGINS`; produção sem origens explícitas → lista vazia; métodos/headers enumerados fora de `development`.

### Riscos aceites

API sem autenticação se exposta publicamente sem gateway — ver [`DEPLOYMENT_INVARIANTS.md`](DEPLOYMENT_INVARIANTS.md).

### Próximos passos (cenário público)

API keys/OAuth2/mTLS + testes de autorização + OpenAPI/UI alinhados ao fluxo completo.

---

## 6. Semgrep

- Job `semgrep` no CI: imagem `semgrep/semgrep`, configs **`p/python`**, **`p/typescript`**, **`p/javascript`**, **`p/react`** sobre `packages` e `apps/web/src`.
- Exclusões: **`.semgrepignore`** na raiz (artefactos, `node_modules`, `.venv`, etc.).
- Política de triagem, `nosemgrep` e evolução: **[`SEMGREP_POLICY.md`](SEMGREP_POLICY.md)**.

---

## 7. Trivy (imagem API)

- Job `trivy-image`: `docker build -f apps/api/Dockerfile -t otm-api:ci .` seguido de `aquasecurity/trivy-action@0.35.0` com `severity: CRITICAL,HIGH` e `exit-code: 1`.
- Complementa pip-audit (Python na host) com visão de **imagem** (OS + dependências instaladas na layer).
