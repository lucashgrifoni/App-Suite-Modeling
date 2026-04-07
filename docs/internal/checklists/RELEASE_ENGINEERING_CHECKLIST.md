# Checklist de engenharia — release readiness

Lista **operacional** para validar o monorepo antes de tag ou publicação. Complementa o checklist de **dia D** em [`LAUNCH_CHECKLIST.md`](LAUNCH_CHECKLIST.md) (artefactos, tag, PyPI).

**Onde correr:** raiz do repositório para Python; `apps/web` para npm.

---

## 1. Gates obrigatórios (comandos)

Marque quando **verde** no branch a publicar.

| # | Gate | Comando (referência) |
|---|------|----------------------|
| 1 | **Typecheck (web)** | `cd apps/web && npm run typecheck` — em Windows com path problemático: `npm run typecheck:portable` |
| 2 | **Build (web)** | `cd apps/web && npm run build` — em Windows: `npm run build:portable` se o wrapper `.cmd` falhar |
| 3 | **Build CI (typecheck + build)** | `cd apps/web && npm run ci:build` (ou `ci:build:portable`) |
| 4 | **Pytest (raiz)** | `python -m pytest` (na raiz do repo) |
| 5 | **OpenAPI alinhado ao código** | `python scripts/verify_openapi_up_to_date.py` **ou** `cd apps/web && npm run contracts:verify` |
| 6 | **E2E crítico (UI)** | `cd apps/web && npm run e2e:critical` (requer `npx playwright install chromium` se ainda não instalado) |
| 7 | **E2E híbrido (API + UI)** | API acessível conforme [`CONTRACTS_CI_HYBRID.md`](../../architecture/CONTRACTS_CI_HYBRID.md); depois `cd apps/web && npm run e2e:hybrid` (inclui `e2e:hybrid:check`) |
| 8 | **Contratos TS gerados** | Após alterar rotas/modelos FastAPI: `cd apps/web && npm run contracts:sync` (export + `openapi-typescript`) |
| 9 | **Verificação pós-sync** | `npm run contracts:verify` e `npm run typecheck` |

**Ordem sugerida local:** (4) pytest → (5) contracts:verify → (1)(2) ou (3) → (6) → (7) se ambiente híbrido estiver pronto.

---

## 2. Documentação e artefatos que devem estar coerentes

- [ ] **`CHANGELOG.md`** — entrada da versão a publicar reflete mudanças reais.
- [ ] **`contracts/openapi.json`** + **`apps/web/src/types/generated/openapi.d.ts`** — regenerados quando a API mudou; `contracts:verify` verde.
- [ ] **Docs de contrato / diff / híbrido** — [`CONTRACT_AND_SNAPSHOTS.md`](../../features/CONTRACT_AND_SNAPSHOTS.md), [`THREAT_MODEL_DIFF.md`](../../features/THREAT_MODEL_DIFF.md), [`CONTRACTS_CI_HYBRID.md`](../../architecture/CONTRACTS_CI_HYBRID.md) alinhadas a scripts e CI.
- [ ] **`KNOWN_LIMITATIONS.md`** — limitações aceites ainda verdadeiras.
- [ ] **[`RELEASE_SCOPE_FREEZE.md`](../decisions/RELEASE_SCOPE_FREEZE.md)** + [`ENGINEERING_CLOSEOUT_SCOPE.md`](../decisions/ENGINEERING_CLOSEOUT_SCOPE.md) — escopo e exclusões aceites para este marco.
- [ ] **README (raiz) e [`docs/README.md`](../../README.md)** — versão, setup e links corretos.

---

## 3. Critérios mínimos “release pronta” (engenharia)

1. Todos os itens da secção **1** marcados (ou exceção **escrita** com dono e data).
2. CI remoto (quando aplicável) reflete os mesmos gates ou um subconjunto documentado como equivalente.
3. Nenhum segredo novo no repositório; diff revisto para dados sensíveis.
4. **Definition of Done** do produto respeitada: [`DEFINITION_OF_DONE.md`](DEFINITION_OF_DONE.md).

---

## 4. Limitações aceites nesta versão (não são bloqueadores)

Ver lista canónica em [`KNOWN_LIMITATIONS.md`](../../KNOWN_LIMITATIONS.md) (sem persistência server-side na UI, sem auth na API out-of-the-box, heurísticas com revisão humana, requisitos E2E/Playwright, notas Windows/Unicode, etc.).

---

## Referências cruzadas

- Gate GO/NO-GO (decisão): [`GO_NO_GO_v0.1.0.md`](GO_NO_GO_v0.1.0.md) — aplicar a versão **declarada** em `pyproject.toml` / `package.json`.
- Congelamento de escopo: [`RELEASE_SCOPE_FREEZE.md`](../decisions/RELEASE_SCOPE_FREEZE.md), [`ENGINEERING_CLOSEOUT_SCOPE.md`](../decisions/ENGINEERING_CLOSEOUT_SCOPE.md).

---

## 5. Histórico — rodada de qualidade (engenharia)

Relatórios operacionais pontuais de “rodada de qualidade” e planos de *staging* de commits foram **fundidos** no presente checklist e em [`CI_AND_SECURITY_EVIDENCE.md`](../../CI_AND_SECURITY_EVIDENCE.md). Para a cronologia de entregas, usar [`CHANGELOG.md`](../../../CHANGELOG.md).
