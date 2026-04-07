# Matriz de achados — auditoria de engenharia completa

**Data:** 2026-04-06  
**Legenda de severidade:** crítica | alta | média | baixa | observação  
**Legenda de status:** confirmado | forte indício | observação | não verificável  
**Confiança:** alta | média | baixa

---

| ID | Categoria | Subcategoria | Severidade | Status | Escopo |
|----|-----------|--------------|------------|--------|--------|
| AUD-APPSEC-001 | AppSec | Autenticação / autorização | alta | confirmado | API + produto |
| AUD-APPSEC-002 | AppSec | Rate limiting / abuso | média | confirmado | API |
| AUD-APPSEC-003 | AppSec | CORS / credenciais | média | confirmado | API |
| AUD-APPSEC-004 | AppSec | Cabeçalhos de segurança (CSP, etc.) | média | forte indício | Frontend estático |
| AUD-APPSEC-005 | AppSec | Armazenamento browser | baixa | observação | Web |
| AUD-ARCH-001 | Arquitetura | Dependência não utilizada | baixa | confirmado | `pyproject.toml` / API |
| AUD-ARCH-002 | Arquitetura | Fronteira core ↔ adapters | — | aderente | Monorepo Python |
| AUD-CLEAN-001 | Clean code | Formatação vs lint | média | confirmado | Python |
| AUD-CLEAN-002 | Clean code | Complexidade / tamanho de módulos | observação | forte indício | `otm_threat_engine` |
| AUD-GOV-001 | Governança | Gates CI vs formatação | média | confirmado | CI |
| AUD-GOV-002 | Governança | Typecheck parcial + mypy permissivo | média | confirmado | Python |
| AUD-GOV-003 | Governança | SAST/secret scanning além do CI | média | confirmado | Pipeline |
| AUD-TEST-001 | Testes | Cobertura frontend unitária | média | confirmado | `apps/web` |
| AUD-TEST-002 | Testes | Suíte Python | — | aderente | `tests/` |
| AUD-SUPPLY-001 | Supply chain | npm moderate (vite/esbuild) | média | confirmado | `apps/web` |
| AUD-DEVX-001 | Engenharia | Deprecation FastAPI/Starlette 422 | baixa | confirmado | API |

---

## Detalhe dos achados (rastreável)

### AUD-APPSEC-001 — API sem autenticação nem autorização

- **Subcategoria:** superfície exposta; controlo de acesso.
- **Severidade:** **alta** se a API estiver exposta a redes não confiáveis; **baixa a média** para uso local/dev documentado.
- **Status:** **confirmado** (ausência de `HTTPBearer`, `OAuth2`, `Depends` de auth em `apps/api`).
- **Ficheiros / evidência:** `apps/api/otm_api/main.py` (sem middleware de auth); `docs/KNOWN_LIMITATIONS.md` (linhas 7–8) alinha discurso com implementação.
- **Princípio violado:** least privilege / defence in depth **no perímetro da API** (quando implantada como serviço de rede).
- **Impacto atual:** qualquer cliente que alcance a API pode invocar análise, import e export — consumo de CPU/memória e potencial fuga de **conteúdo de modelos** submetidos (dados sensíveis do utilizador no payload, não “segredos da app”).
- **Risco futuro:** implantação pública sem gateway = abuso e exposição de dados de threat model.
- **Recomendação (alto nível):** API atrás de autenticação (API key/OIDC) + gateway com rate limit para cenários não locais; documentar modelo de ameaça da implantação.
- **Confiança:** alta.

### AUD-APPSEC-002 — Ausência de rate limiting na API

- **Severidade:** **média** (DoS lógico / custo de compute).
- **Status:** **confirmado** (grep sem `slowapi`, `rate_limit`, etc. na API).
- **Evidência:** endpoints de análise e import aceitam pedidos sem throttle; único limite explícito observado: tamanho de upload 2 MiB em `apps/api/otm_api/routers/imports.py` (`_MAX_BYTES`).
- **Princípio violado:** controlo de abuso em superfície pública.
- **Confiança:** alta.

### AUD-APPSEC-003 — CORS com `allow_credentials=True`

- **Severidade:** **média** em `development`/`staging` com origens amplas; **baixa** em `production` com `origins=[]` quando `OTM_CORS_ORIGINS` não definido.
- **Status:** **confirmado**.
- **Evidência:** `apps/api/otm_api/main.py` + `apps/api/otm_api/cors_settings.py` — em dev, `methods` e `headers` como `*`.
- **Impacto:** combinação credentialed CORS + origens mal configuradas em staging poderia ampliar impacto de XSS de terceiros (cenário mais teórico se não houver cookies sensíveis da API).
- **Confiança:** média.

### AUD-APPSEC-004 — Sem CSP / hardening explícito no frontend Vite

- **Severidade:** **média** (defesa em profundidade).
- **Status:** **forte indício** (grep sem `Content-Security-Policy` em `apps/web`).
- **Evidência:** `apps/web/vite.config.ts` não define headers de segurança; aplicação é SPA — endurecimento típico fica em CDN/reverse proxy ou plugin.
- **Confiança:** média.

### AUD-APPSEC-005 — sessionStorage / localStorage para documento e histórico

- **Severidade:** **baixa** (observação de modelo de ameaça).
- **Status:** **observação**.
- **Evidência:** `SessionContext.tsx`, `analysisHistoryStorage.ts`, `diagramLayoutStorage.ts`, etc.
- **Impacto:** XSS no mesmo origin poderia ler modelos locais; sem CSP, risco residual depende de superfície XSS na app (não mapeada como vulnerabilidade confirmada nesta auditoria).
- **Confiança:** média.

### AUD-ARCH-001 — SQLAlchemy listado em extras `api` sem uso no código da API

- **Severidade:** **baixa**.
- **Status:** **confirmado** (grep sem `sqlalchemy` em `apps/api`).
- **Evidência:** `pyproject.toml` `[project.optional-dependencies] api`; `docs/architecture/ARCHITECTURE.md` prevê BD pós-MVP.
- **Princípio violado:** YAGNI / dependências mínimas (leve).
- **Confiança:** alta.

### AUD-ARCH-002 — Fronteira core vs adapters

- **Status:** **aderente** com evidência automatizada.
- **Evidência:** `python scripts/check_core_adapter_boundary.py` exit 0; testes `tests/test_core_adapter_boundary.py`.

### AUD-CLEAN-001 — Drift de formatação (Ruff)

- **Severidade:** **média** (governança e legibilidade consistente).
- **Status:** **confirmado**.
- **Evidência:** `ruff format --check` — 73 ficheiros a reformatar.
- **Confiança:** alta.

### AUD-CLEAN-002 — Módulos grandes no motor

- **Severidade:** **observação**.
- **Status:** **forte indício** (amostragem: `engine.py`, `registry_data.py`, lenses); não contagem exaustiva de LOC nesta auditoria.
- **Risco:** manutenção e revisão mais custosas.
- **Confiança:** média.

### AUD-GOV-001 — CI não valida `ruff format`

- **Severidade:** **média**.
- **Status:** **confirmado** (`.github/workflows/ci.yml` só `ruff check`).
- **Confiança:** alta.

### AUD-GOV-002 — Mypy parcial + `ignore_missing_imports`

- **Severidade:** **média**.
- **Status:** **confirmado** (`pyproject.toml`).
- **Impacto:** erros de tipo em pacotes não cobertos ou imports sem stubs podem escapar.
- **Confiança:** alta.

### AUD-GOV-003 — Sem Bandit/Semgrep/Trivy/Checkov no pipeline

- **Severidade:** **média** (maturidade AppSec).
- **Status:** **confirmado** (workflow inspecionado).
- **Confiança:** alta.

### AUD-TEST-001 — Poucos testes unitários TS no front

- **Severidade:** **média**.
- **Status:** **confirmado** (Vitest: 2 ficheiros); E2E no CI compensa parcialmente.
- **Confiança:** alta.

### AUD-TEST-002 — Suíte Python extensa

- **Status:** **aderente** — 408 testes passando; contratos OpenAPI, docs, engine, CLI, API.

### AUD-SUPPLY-001 — npm audit moderate (esbuild/vite)

- **Severidade:** **média** no contexto de dev server; **baixa** em produção build estático se não expor dev server.
- **Status:** **confirmado** (output `npm audit`).
- **Confiança:** alta.

### AUD-DEVX-001 — DeprecationWarning HTTP 422

- **Severidade:** **baixa**.
- **Status:** **confirmado** (pytest warnings).
- **Ficheiros:** `apps/api/otm_api/routers/_errors.py`, `exports.py`.
- **Confiança:** alta.

### AUD-DEVX-002 — `shell=True` no Windows para npm (`dev_env.py`)

- **Severidade:** **baixa** (scripts de desenvolvimento).
- **Status:** **observação** com justificativa documentada no ficheiro.
- **Evidência:** `scripts/dev_env.py` linhas 48–54.
- **Confiança:** alta.

---

*Fim da matriz. IDs são estáveis para referência em PRs e planos de remediação.*
