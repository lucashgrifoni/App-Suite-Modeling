# Resumo final — higiene rodada 2

**Data:** 2026-04-06

---

## 1. Resumo executivo

A **round 2** tratou **todo o `docs/`** como produto curado: eliminou **paralelismos** (BRUTAL vs FULL_PROJECT, múltiplos relatórios de execução CI, trilhos UI *plan/validation/handoff*, documentos de fecho só com valor histórico) e **fundiu** o conhecimento ainda útil em **poucos anfitriões** + **três novos índices** (`CI_AND_SECURITY_EVIDENCE`, `GITHUB_README_AND_METADATA`, `FRONTEND_UI_ROLLOUT_HISTORY`). A round 1 (`docs/archive/`) mantém-se contabilizada separadamente no histórico do branch.

---

## 2. Métricas reais

| Métrica | Valor |
|---------|--------|
| Ficheiros `docs/*.md` removidos do **Git** (round 2, sem `archive/`) | **38** |
| Ficheiros `docs/*.md` apagados localmente (**untracked**) | **8** |
| Novos documentos consolidadores + relatórios round 2 | **6** |
| Documentos anfitriões estendidos (merge de conteúdo) | **10+** |
| Blocos de comentário removidos em código | **0** (sem alvo seguro identificado) |
| `TODO`/`FIXME`/`HACK`/`XXX` encontrados em `py`/`ts`/`tsx` | **0** |

---

## 3. Diferença: cautela legítima vs conservadorismo excessivo

- **Excesso de cautela (round 1):** manter `BRUTAL_*` e `FULL_PROJECT_*` como se fossem “governanças” distintas quando **80%+** do backlog era o mesmo conjunto de riscos. **Round 2:** um backlog + plano canónico, tabela de mitigações e itens BL-16–18 para o que era exclusivo do ramo BRUTAL.
- **Cautela legítima:** não fundir `REMEDIATION_BACKLOG.md` (produto) com `FULL_PROJECT_REMEDIATION_BACKLOG.md` (engenharia do repo).
- **Cautela legítima:** não apagar ADRs, `KNOWN_LIMITATIONS`, contratos ou testes sem substituição.

---

## 4. `.gitignore`

Sem alteração nesta round (já ajustado na round 1 para `htmlcov/`).

---

## 5. Validações executadas

| Comando | Resultado |
|---------|-----------|
| `python -m ruff check packages apps tests` | **OK** |
| `python -m pytest -q` | **OK** — 391 passed; 3 `DeprecationWarning` (FastAPI 422) |
| `python -m mypy packages/core-schema/otm_core_schema apps/api/otm_api` | **OK** |
| `python scripts/verify_openapi_up_to_date.py` | **OK** |
| `npm run ci:build:portable` (em `apps/web`) | **OK** |
| `npm run test` (em `apps/web`) | **OK** — 9 tests Vitest |

**Não executado:** Playwright `e2e:hybrid` / `e2e:critical` completos (dependem de stack; continuam no CI).

---

## 6. Status final

### **CLEAN WITH CAVEATS**

- **CLEAN** no sentido de: documentação redundante em `docs/` **fortemente reduzida**; índice `docs/README.md` atualizado; links internos críticos (`DEPLOYMENT_INVARIANTS` → evidência CI) corrigidos.  
- **CAVEATS:** `CHANGELOG.md` histórico ainda menciona nomes de ficheiros apagados (propositadamente, como arquivo editorial); working tree do utilizador pode conter outras alterações não relacionadas (i18n, etc.).

---

## 7. Ficheiros-chave desta round

**Novos:** `CI_AND_SECURITY_EVIDENCE.md`, `GITHUB_README_AND_METADATA.md`, `FRONTEND_UI_ROLLOUT_HISTORY.md`, `PROJECT_HYGIENE_ROUND2_*`.  

**Editados (além dos anfitriões):** `docs/README.md`, `docs/DEPLOYMENT_INVARIANTS.md`, `CHANGELOG.md`.
