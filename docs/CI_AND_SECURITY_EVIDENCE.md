# Evidência consolidada — CI, tipagem, SCA, CLI, observabilidade e perímetro da API

Documento único que substitui relatórios de execução dispersos (rodada de higiene docs, 2026-04).  
**Índice:** [Mypy](#1-mypy-no-ci-gradual) · [SCA](#2-sca-supply-chain) · [CLI modular](#3-refatoração-da-cli) · [Observabilidade](#4-observabilidade-da-api) · [Perímetro / CORS](#5-endurecimento-de-perímetro-da-api)

---

## 1. Mypy no CI (gradual)

### Módulos cobertos inicialmente

- `packages/core-schema/otm_core_schema`
- `apps/api/otm_api`

Comando no CI (job `python`):

```bash
mypy packages/core-schema/otm_core_schema apps/api/otm_api
```

### Strictness

- Configuração global em `[tool.mypy]` no `pyproject.toml` (`python_version`, `warn_unused_ignores`, `show_error_codes`).
- `ignore_missing_imports = true` **no global** para não explodir o legado de stubs de terceiros; a adoção é **por pastas** no comando CI (não “mypy em todo o monorepo” de uma vez).

### Roadmap de expansão

1. `packages/threat-engine/otm_threat_engine`
2. `packages/exporters`, `packages/artifact-import`
3. `apps/cli/otm_cli` (após estabilizar a refatoração modular)
4. Reduzir `ignore_missing_imports` global substituindo por `[[tool.mypy.overrides]]` por pacote

### Critérios de aceite

- Job `Mypy (core-schema + API)` no `.github/workflows/ci.yml` falha em erros reais nos diretórios listados.

---

## 2. SCA (supply chain)

### Ferramentas

| Stack | Ferramenta | Onde |
|-------|------------|------|
| Python | **pip-audit** (OSV/PyPI) | Job `python` no CI, após `pip install -e ".[dev,cli,api]"` |
| Node | **npm audit** | Job `web`, `apps/web`, após `npm ci` |

### Thresholds

- **Python:** `python -m pip_audit --desc on -S .` — gate estrito (qualquer vulnerabilidade conhecida falha o CI na árvore resolvida).
- **Node:** `npm audit --audit-level=critical`

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
