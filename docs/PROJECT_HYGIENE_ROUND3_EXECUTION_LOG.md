# Log de execução — higiene rodada 3

**Data:** 2026-04-07

---

## 1. Removidos (`docs/I18N_*.md`)

Remoção por `Get-ChildItem docs -Filter I18N_*.md | Remove-Item` (ficheiros **não** canónicos). **Preservado:** `docs/I18N.md`.

Ficheiros eliminados do working tree (lista de basenames):

- `I18N_DECISIONS.md`
- `I18N_IMPLEMENTATION_PLAN.md`
- `I18N_TEST_CHECKLIST.md`
- `I18N_ROLLOUT_NOTES.md`
- `I18N_EXPORTS_IMPLEMENTATION.md`
- `I18N_EXPORTS_DECISIONS.md`
- `I18N_EXPORTS_TEST_CHECKLIST.md`
- `I18N_FINAL_STATE.md`
- `I18N_GAPS_CLOSED.md`
- `I18N_KNOWN_LIMITATIONS.md`
- `I18N_GLOSSARY.md`
- `I18N_FINAL_AUDIT_REPORT.md`
- `I18N_FINAL_AUDIT_SCORECARD.md`
- `I18N_HARDCODE_AUDIT.md`
- `I18N_LOCALE_CONSISTENCY_MATRIX.md`
- `I18N_RELEASE_DECISION.md`

*(Contagem: 16 ficheiros — conforme glob pré-execução menos duplicados de path.)*

---

## 2. Criados

- `docs/I18N.md` — documento canónico único.
- `docs/PROJECT_HYGIENE_ROUND3_AUDIT_REPORT.md`
- `docs/PROJECT_HYGIENE_ROUND3_EXECUTION_LOG.md` (este ficheiro)
- `docs/PROJECT_HYGIENE_ROUND3_FINAL_SUMMARY.md`

---

## 3. Editados

- `docs/PREMIUM_REPORTS.md` — link `I18N_FINAL_STATE` → `I18N.md`
- `docs/README.md` — entrada `I18N.md` no índice
- `CHANGELOG.md` — [Unreleased] Added/Removed; bullet relatórios CI; notas editoriais em `[7.0.0]`, `[6.0.0]`, `[5.0.0]`
- `apps/api/otm_api/observability.py` — imports reorganizados (Ruff I001; gate pós-R3)

---

## 4. Não executado (explícito)

- `git add` em massa de código `??` (CLI modular, API, web i18n) — permanece para commit de feature pelo autor.
- Alteração de `.gitignore` — sem novo padrão recorrente identificado.
- Nova pasta ou renomeação de módulos.

---

## 5. Verificação de links

- `grep` por `I18N_FINAL_STATE`, `I18N_DECISIONS` em `*.md` após mudanças: limpo em docs de produto (menções restantes apenas em relatórios R3 que listam ficheiros removidos).

---

## 6. Validação final (pós-R3)

| Comando | Resultado |
|---------|-----------|
| `python -m ruff check packages apps tests` | OK (correção **I001** aplicada com `--fix` em `apps/api/otm_api/observability.py`) |
| `python -m pytest -q --tb=no` | 404 passed |
| `python -m mypy packages/core-schema/otm_core_schema apps/api/otm_api` | Success |
| `python scripts/verify_openapi_up_to_date.py` | OK |
| `npm run ci:build:portable` (`apps/web`) | OK |
| `npm run test` (`apps/web`, Vitest) | 9 passed |
