# Próximos passos — estado após remediação (2026-04-06+)

> **Registo datado — não é o estado corrente do projeto.** Este documento descreve a
> versão que existia quando foi escrito; parte do que afirma já foi corrigido. Ver
> [`docs/internal/README.md`](../README.md) antes de citar qualquer conclusão daqui.


Este documento substitui o plano “somente auditoria”: as linhas abaixo indicam **o que já foi executado** no repositório e **o que permanece backlog** real.

---

## Concluído (implementado e validado no código / CI)

### Quick wins (auditoria original)

- [x] Gate **`ruff format --check`** no CI + formatação alinhada.
- [x] **`HTTP_422_UNPROCESSABLE_CONTENT`** (Starlette/FastAPI).
- [x] **`docs/architecture/DEPLOYMENT_INVARIANTS.md`** — API sem auth por defeito + gateway; mais tarde ampliado com variáveis de perímetro.
- [x] **`.gitleaksignore`** para scans locais `--no-git`.

### Alto impacto / baixo risco

- [x] Vitest para **`diagramSanitize`**.
- [x] Comentário **SQLAlchemy** reservado no extra `api`.
- [x] **Bandit** no CI + dependência `[dev]`.
- [x] **Mypy monorepo** — todos os pacotes `packages/*`, `apps/cli`, `apps/api` no job CI; correcções de tipos (loops `for`, `StrideCategory`, `document_json`, `ai_import_corpus`, etc.).
- [x] **Vite 6 / Vitest 3** — `npm audit` moderate resolvido na árvore actual de `apps/web`.
- [x] **Semgrep** — job CI (`p/python`, `p/typescript`, `p/javascript`, `p/react`) em `packages` e `apps/web/src`.
- [x] **Trivy** — build `apps/api/Dockerfile` + scan imagem CRITICAL/HIGH.
- [x] **npm audit moderate** como gate no job `web` (além de critical).
- [x] **API opcionalmente protegida:** `OTM_API_KEY` + middleware `OptionalApiKeyMiddleware` (cabeçalhos `X-OTM-API-Key` / `Bearer`).
- [x] **Rate limiting:** `slowapi` + `OTM_RATE_LIMIT` / defeito staging+prod `120/minute` / `OTM_RATE_LIMIT_DISABLED`; E2E híbrido com `OTM_RATE_LIMIT_DISABLED=1` no `playwright.hybrid.config.ts`.
- [x] Testes **`test_api.py`** para API key.
- [x] Documentação: **`docs/features/API.md`**, **`CI_AND_SECURITY_EVIDENCE.md`**, **`KNOWN_LIMITATIONS.md`**.

---

## Backlog (não feito neste ciclo)

### Alto impacto / alto risco

- [ ] **OAuth2/OIDC** completo (não só API key estática).
- [ ] **Persistência server-side** (SQLAlchemy + modelo multi-tenant).
- [ ] **Rate limit distribuído** (Redis / gateway) em vez de só in-process SlowAPI.

### Arquitetura / qualidade

- [ ] Reduzir **`ignore_missing_imports`** global com overrides por pacote e stubs.
- [ ] Remover **`# type: ignore[call-arg]`** em `builders.py` quando o plugin Pydantic/mypy alinhar com `ThreatModelDocument`.
- [ ] Particionar módulos muito grandes do motor (`engine.py`, `registry_data.py`, …) com PRs orientados por testes.

### AppSec / front

- [x] **CSP** e cabeçalhos: `public/_headers`, `vite.config.ts` (dev sem CSP; `preview` com CSP), `public/theme-init.js`, `docs/features/SECURITY_HEADERS.md`.
- [x] **Semgrep** extra (`p/javascript`, `p/react`), **`.semgrepignore`**, **`docs/architecture/SEMGREP_POLICY.md`**.
- [x] **pre-commit** opcional: **`.pre-commit-config.yaml`**, **`docs/architecture/PRE_COMMIT.md`** (Ruff + mypy parcial core-schema + API).

### Documentação / governação

- [ ] Cruzar **`FULL_PROJECT_REMEDIATION_BACKLOG.md`** com IDs da auditoria (deduplicação).
- [ ] Badge CI no **README** após publicação do repositório.

### Testes

- [ ] Mais testes de integração para **rate limit** (opcional; hoje o defeito em `development` evita flakiness na suíte principal).

---

*Última actualização: alinhada às alterações de CI, API, npm e mypy monorepo.*
