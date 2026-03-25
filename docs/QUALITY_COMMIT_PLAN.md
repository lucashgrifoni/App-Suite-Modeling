## Plano de commits (rodada de qualidade) — sem quebrar nada

Objetivo: facilitar publicar a rodada de qualidade em commits pequenos e revisáveis, **sem misturar** com mudanças maiores já existentes no workspace.

> Nota: este arquivo **não executa commit**; é apenas um guia de staging/ordenação.

---

### Commit 1 — `test: add snapshot/contract tests for exporters`

Inclui (alto valor / baixo risco):
- `tests/test_exporters.py`
- `tests/snapshots/analysis_markdown_minimal_harmonized.md`

Opcional (se quiser manter junto do commit de testes do bundle/mermaid):
- `tests/test_api.py` (contratos de erro HTTP)
- `tests/test_cli.py` (contratos CLI)

---

### Commit 2 — `refactor(exporters): improve cohesion without output changes`

Inclui:
- `packages/exporters/otm_exporters/analysis_markdown.py`
- `packages/exporters/otm_exporters/bundle_json.py`
- `packages/exporters/otm_exporters/document_json.py`
- `packages/exporters/otm_exporters/mermaid_flowchart.py`
- `packages/exporters/otm_exporters/__init__.py`

Garantias:
- Snapshot do Markdown e contratos determinísticos mantêm o output.

---

### Commit 3 — `refactor(api): dedupe document parsing and normalize error detail`

Inclui:
- `apps/api/otm_api/routers/_errors.py` (novo helper)
- `apps/api/otm_api/routers/models.py`
- `apps/api/otm_api/routers/exports.py`
- `apps/api/otm_api/routers/templates.py`
- `apps/api/otm_api/services/exports.py`
- `apps/api/otm_api/services/templates_catalog.py`

E seus testes:
- `tests/test_api.py`

---

### Commit 4 — `refactor(cli): dedupe output writing; keep UX stable`

Inclui:
- `apps/cli/otm_cli/cli.py`
- `tests/test_cli.py`

---

### Commit 5 — `refactor(web): improve API error messages; reduce type duplication`

Inclui:
- `apps/web/src/api/client.ts`
- `apps/web/src/api/otmApi.ts`

Se fizer parte da mesma rodada (verificar se são mudanças “qualidade” e não feature):
- `apps/web/src/pages/AnalysisPage.tsx`
- `apps/web/src/pages/WizardPage.tsx`
- `apps/web/src/types/methodology.ts`
- `apps/web/src/constants/methodologyMeta.ts`
- `apps/web/playwright.config.ts`
- `apps/web/e2e/smoke.spec.ts`
- `apps/web/package.json`
- `apps/web/package-lock.json`

---

### Commit 6 — `docs: add engineering quality round report`

Inclui:
- `docs/ENGINEERING_QUALITY_ROUND_REPORT.md`
- `docs/QUALITY_COMMIT_PLAN.md`

---

### Itens fora da rodada de qualidade (manter separados)

Pelo `git status`, existem muitos arquivos novos/modificados que aparentam ser entregas maiores:
- `packages/threat-engine/otm_threat_engine/**` (múltiplos módulos novos)
- `examples/test-apps/**`, `fixtures/**`, `scripts/**`
- vários `docs/FINAL_*.md`, `docs/STRIDE_GENERICITY_*`, etc.

Sugestão: colocar isso em commits próprios (`feat:`/`docs:`/`chore:`) ou numa PR separada, para a rodada de qualidade não ficar “misturada”.

---

### Checklist rápido antes de commitar (manual)
- `python -m pytest`
- `python -m pytest tests/test_smoke_release_candidate.py`
- `python scripts/run_global_regression_gate.py`

