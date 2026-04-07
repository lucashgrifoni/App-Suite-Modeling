# Relatório — reorganização de `/docs`

**Data:** 2026-04-01  
**Objectivo:** Passar de um plano plano de Markdown na raiz de `docs/` para uma hierarquia **pública / features / architecture / internal**, sem apagar conteúdo e com links corrigidos.

---

## O que foi movido

### Mantidos na raiz de `docs/`

- `README.md` — reescrito como hub único  
- `MONOREPO.md`, `REPOSITORY_LAYOUT.md`, `PROJECT_DEEP_DIVE.md`  
- `KNOWN_LIMITATIONS.md`, `VERSIONING_AND_TAGS.md`, `CI_AND_SECURITY_EVIDENCE.md`  
- Novos: `DOCUMENTATION_STRUCTURE.md`, `DOCS_REORGANIZATION_REPORT.md` (este ficheiro)

### `docs/features/` (24 ficheiros)

Guias de produto e superfícies: `API`, `CLI`, `UI`, `ARTIFACT_IMPORT`, `THREAT_MODEL_DIFF`, `EXPORTERS`, `PREMIUM_REPORTS`, `REMEDIATION_BACKLOG`, `EXPLAINABILITY`, `TEMPLATES_AND_PACKS`, `TEMPLATE_CATALOG`, `CHOOSE_METHODOLOGY`, `MULTI_ENGINE_ARCHITECTURE`, `PLOT4AI_AI_SYSTEM`, `I18N`, `CONTRACT_AND_SNAPSHOTS`, `SCHEMA_V1`, `CORE_ENGINE`, `MVP_ROADMAP`, `PRODUCT_POSITIONING`, `BRANDING`, `SCREENSHOT_GUIDE`, `MODELING_QUALITY`, `SECURITY_HEADERS`.

### `docs/architecture/` (7 + ADRs)

- `ARCHITECTURE.md`, `DESIGN_SYSTEM_FOUNDATION.md`, `CONTRACTS_CI_HYBRID.md`, `DEPLOYMENT_INVARIANTS.md`, `PRE_COMMIT.md`, `SEMGREP_POLICY.md`, `SMOKE_VALIDATION.md`  
- `adr/` — movido de `docs/adr/` para `docs/architecture/adr/`

### `docs/internal/audits/` (7)

`FULL_ENGINEERING_*` (exceto NEXT_ACTIONS e TOOL_LOG), `FULL_PROJECT_CLEAN_ARCHITECTURE_AUDIT`, `FULL_PROJECT_QUALITY_SCORECARD`, `SONAR_DECISION_REPORT`.

### `docs/internal/logs/` (2)

`FULL_ENGINEERING_TOOL_EXECUTION_LOG`, `FINAL_RELEASE_EXECUTION_LOG`.

### `docs/internal/reports/` (12)

Inclui `FINAL_GO_NO_GO_*`, `FINAL_RELEASE_SCORECARD`, `VALIDATION_REPORT_*`, `RELEASE_NOTES_*`, `FULL_ENGINEERING_NEXT_ACTIONS`, remediação, risco residual, histórico UI, `GITHUB_README_AND_METADATA`, etc.

### `docs/internal/decisions/` (5)

`STRIDE_GENERICITY_REDUCTION_DECISION`, `E2E_GATE_DECISION`, `ENGINEERING_CLOSEOUT_SCOPE`, `RELEASE_SCOPE_FREEZE`, `NEXT_PHASE_RECOMMENDATIONS`.

### `docs/internal/checklists/` (7)

`LAUNCH_CHECKLIST`, `RELEASE_ENGINEERING_CHECKLIST`, `RELEASE_CHECKLIST_RC`, `PREPUBLISH_CHECKLIST`, `DEFINITION_OF_DONE`, `GO_NO_GO_v0.1.0`, `PUBLISH_PLAYBOOK`.

### `docs/screenshots/`

Inalterado (apenas `README.md` de orientação, com links actualizados).

---

## O que foi agrupado

- **Superfície única de produto** → `features/`.  
- **Decisão e política de engenharia** → `architecture/` + `adr/`.  
- **Material de auditoria, release e histórico** → `internal/*`.

---

## O que foi mantido sem alteração de *conteúdo* técnico

- Corpo dos documentos (regras de negócio, tabelas, decisões) — **não** reescritos; apenas **caminhos** e **alguns links relativos** ajustados.  
- Código-fonte da aplicação — sem mudanças de comportamento; referência em `otm_api.main` actualizada para `docs/features/API.md`.

---

## Referências actualizadas (fora de `docs/`)

- `README.md` (raiz) — links para `docs/features/…`, `docs/architecture/…`, `docs/internal/…`  
- `tests/test_docs_methodologies.py` — caminhos dos ficheiros lidos  
- `scripts/docs_apply_path_migration.py` — substituição global `docs/X` → novo caminho (uso pontual)  
- `.github/ISSUE_TEMPLATE/feature_request.yml`, `.pre-commit-config.yaml` (comentário), `CHANGELOG.md` (entradas históricas podem ainda mostrar caminhos antigos no texto — não alterado em bloco)

---

## O que pode ser removido ou fundido **no futuro** (não feito nesta rodada)

| Sugestão | Severidade | Nota |
|----------|------------|------|
| Fundir vários `FULL_ENGINEERING_*.md` num único índice em `internal/audits/README.md` | Baixa | Reduz duplicação de cabeçalhos; requer revisão humana |
| Arquivar `RELEASE_NOTES_RC1/RC2` num único `internal/reports/historical/` | Baixa | Cosmético |
| Actualizar linhas antigas do `CHANGELOG.md` com novos caminhos | Opcional | Historiadores preferem datas; links absolutos ao Git resolvem |

---

## Validação

Executar na raiz do repositório:

```bash
python -m pytest tests/test_docs_links.py tests/test_docs_methodologies.py -q
```

---

*Fim do relatório de reorganização.*
