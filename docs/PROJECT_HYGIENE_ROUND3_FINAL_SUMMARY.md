# Resumo final — higiene rodada 3 (fecho canónico)

**Data:** 2026-04-07  
**Estado:** **CLEAN WITH EXPLICIT MINOR CAVEATS** (ver §5)

---

## 1. Objetivo

Fechar resíduos pós-rodada 2: pacote `docs/I18N_*.md`, referências editoriais obsoletas, índices e changelog coerentes, sem nova reestruturação.

---

## 2. O que foi feito (síntese)

| Área | Resultado |
|------|-----------|
| **I18N** | Um único **`docs/I18N.md`** canónico; removidos **16** `docs/I18N_*.md` (shards não canónicos). |
| **Cross-links** | `docs/PREMIUM_REPORTS.md` → `I18N.md`; `docs/README.md` com entrada no índice. |
| **CHANGELOG** | [Unreleased] e notas editoriais em versões antigas alinhadas a ficheiros existentes / contexto histórico. |
| **`.gitignore`** | Sem alteração (padrões existentes suficientes para R3). |
| **Artefactos R3** | `PROJECT_HYGIENE_ROUND3_AUDIT_REPORT.md`, `EXECUTION_LOG.md`, este `FINAL_SUMMARY.md`. |

---

## 3. Validação executada (comandos reais)

Executados na raiz do repositório e em `apps/web`, após correção pontual Ruff (§5).

| Comando | Resultado |
|---------|-----------|
| `python -m ruff check packages apps tests` | **OK** (após `--fix` em `observability.py`) |
| `python -m pytest -q --tb=no` | **404 passed** (6 DeprecationWarnings conhecidos em FastAPI/Starlette) |
| `python -m mypy packages/core-schema/otm_core_schema apps/api/otm_api` | **Success: no issues** |
| `python scripts/verify_openapi_up_to_date.py` | **OK** (OpenAPI em disco sincronizado) |
| `npm run ci:build:portable` (em `apps/web`) | **OK** |
| `npm run test` (Vitest, em `apps/web`) | **9 passed** (2 ficheiros) |

---

## 4. Critérios de sucesso (checklist)

- [x] Sem proliferação I18N em `docs/` — só `I18N.md` + menções em índice/PREMIUM/CHANGELOG.
- [x] Referências óbvias a `I18N_FINAL_STATE` / `I18N_DECISIONS` fora de docs de produto: **ausentes** (restam apenas citações nos próprios relatórios R3, como lista do que foi removido).
- [x] Índice `docs/README.md`, `PREMIUM_REPORTS` e changelog coerentes com a árvore atual.
- [x] Gates Python + build web + testes unitários web executados com sucesso.

---

## 5. Caveats explícitos (menores)

1. **Working tree Git:** permanecem muitos ficheiros `??` / `M` fora do escopo editorial R3 (CLI modular, API, web i18n, dependabot, etc.). A R3 **não** fez `git add` em massa nem commit — estado “limpo canónico” refere-se a **estrutura documental e links**, não a um `git status` vazio.
2. **Correção mínima fora de `docs/`:** `apps/api/otm_api/observability.py` — **Ruff I001** corrigido com `ruff check … --fix` para o gate `ruff check packages apps tests` passar após validação pós-R3.

---

## 6. Ficheiros criados ou alterados nesta rodada (lista)

**Criados**

- `docs/I18N.md`
- `docs/PROJECT_HYGIENE_ROUND3_AUDIT_REPORT.md`
- `docs/PROJECT_HYGIENE_ROUND3_EXECUTION_LOG.md`
- `docs/PROJECT_HYGIENE_ROUND3_FINAL_SUMMARY.md` (este ficheiro)

**Editados**

- `docs/PREMIUM_REPORTS.md`
- `docs/README.md`
- `docs/PROJECT_HYGIENE_ROUND3_EXECUTION_LOG.md` (validação e secção de links)
- `docs/PROJECT_HYGIENE_ROUND3_AUDIT_REPORT.md` (contagem I18N alinhada)
- `CHANGELOG.md` (incl. [Unreleased] **Fixed** — Ruff I001)
- `apps/api/otm_api/observability.py` (ordem de imports, Ruff)

**Removidos (working tree)**

- `docs/I18N_*.md` (16 ficheiros; ver log de execução para basenames)

---

## 7. Decisões autónomas

- Consolidar I18N num único documento em vez de ignorar shards no `.gitignore` (evita “lixo” versionável ambíguo).
- Preservar texto histórico no CHANGELOG com notas editoriais curtas onde ficheiros citados já não existem.
- Corrigir I001 em `observability.py` como parte do fecho de qualidade, sem abrir refactor da API.

---

## 8. Follow-up opcional (fora de R3)

- Commit separado: apenas `docs/` + `CHANGELOG.md` + fix `observability.py`, ou agrupar com o PR de features conforme política da equipa.
- Tratar DeprecationWarnings `HTTP_422_UNPROCESSABLE_ENTITY` quando atualizar dependências FastAPI/Starlette.
