# Auditoria de higiene — rodada 2 (agressiva)

**Data:** 2026-04-06  
**Objetivo:** ir **além** da remoção de `docs/archive/`: reduzir museu operacional, fundir backlogs/relatórios paralelos e preservar só conhecimento durável com rastreabilidade.

---

## 1. Executive summary

Foi feita uma **reauditoria em todo o monorepo** com foco em `docs/`: identificação de **duplicidade funcional** (dois backlogs de engenharia, dois scorecards, múltiplos relatórios de execução CI, trilhos UI *plan/validation/handoff*, fechos “round/final/closeout” só referenciados pelo CHANGELOG).

**Decisão:** consolidar conteúdo **exclusivo e ainda verdadeiro** nos documentos-base (`FULL_PROJECT_*`, `EXPLAINABILITY`, `THREAT_MODEL_DIFF`, `STRIDE_GENERICITY_REDUCTION_DECISION`, checklists de release) e **remover** ficheiros concorrentes ou transitórios. Criar **três** novos índices consolidados (`CI_AND_SECURITY_EVIDENCE`, `GITHUB_README_AND_METADATA`, `FRONTEND_UI_ROLLOUT_HISTORY`).

**Cautela legítima vs conservadorismo excessivo (explicitado):**

| Situação | Classificação |
|----------|----------------|
| Dois backlogs de engenharia (BL-* vs B-*) com ~80% de sobreposição | **Conservadorismo excessivo na R1** — aqui fundido num único backlog + tabela de mitigações. |
| Manter `BRUTAL_AUDIT` e `FULL_PROJECT_CLEAN_ARCHITECTURE_AUDIT` em paralelo | **Ruído** — um diagnóstico longo basta; nota de fusão no audit “clean”. |
| `REMEDIATION_BACKLOG.md` (produto) vs `FULL_PROJECT_REMEDIATION_BACKLOG.md` | **Cautela legítima** — propósitos diferentes; **preservado** o de produto sem tocar. |
| ADRs, `KNOWN_LIMITATIONS`, contratos, `tests/`, `scripts/` referenciados por CI/docs | **Preservação** — fora de remoção. |

---

## 2. Scope analyzed

- `docs/**/*.md` (118 → pós-limpeza reduzido)
- Referências cruzadas (`grep` em `*.md`, `*.py`, `*.yml`)
- `scripts/` (uso real: CI, `docs/*.md`, `CONTRACT_AND_SNAPSHOTS`)
- Código: `TODO`/`FIXME`/`HACK`/`XXX` em `py/ts/tsx` — **nenhuma ocorrência** na pesquisa

---

## 3. Methodology

1. Listagem por padrão de nome (`FINAL_*`, `ROUND*`, `BRUTAL_*`, `FRONTEND_*`, `*_EXECUTION_REPORT`, etc.).
2. `grep` de referências no repositório (excluindo CHANGELOG histórico).
3. Leitura amostral de pares redundantes (backlogs, planos, scorecards).
4. Consolidação **no melhor anfitrião** (já indexado ou semanticamente central).
5. `git rm` para ficheiros rastreados; `Delete` para cópias **untracked** locais (relatórios de execução / higiene R1 que nunca entraram no índice).
6. Atualização de `docs/README.md`, `DEPLOYMENT_INVARIANTS.md`, `CHANGELOG.md` [Unreleased].

---

## 4. Findings por categoria

### 4.1 Candidatos **consolidar e remover**

| Grupo | Anfitrião | Removidos |
|-------|-----------|-----------|
| Backlog + plano BRUTAL (paralelos) | `FULL_PROJECT_REMEDIATION_BACKLOG.md`, `FULL_PROJECT_REMEDIATION_PLAN.md` | `BRUTAL_REMEDIATION_BACKLOG.md`, `BRUTAL_REMEDIATION_PLAN.md` |
| Scorecard BRUTAL | `FULL_PROJECT_QUALITY_SCORECARD.md` | `BRUTAL_SCORECARD.md` |
| Auditoria BRUTAL | `FULL_PROJECT_CLEAN_ARCHITECTURE_AUDIT.md` (nota no topo) | `BRUTAL_AUDIT_REPORT.md` |
| Relatórios CI/API/CLI dispersos | `CI_AND_SECURITY_EVIDENCE.md` (novo) | 5 relatórios `*_EXECUTION_REPORT` + perímetro (ver log) |
| README release validação + handoff | `GITHUB_README_AND_METADATA.md` (novo) | `README_RELEASE_*.md` |
| 5×3 documentos UI (plan/val/handoff) | `FRONTEND_UI_ROLLOUT_HISTORY.md` (novo) + `UI.md` / `DESIGN_SYSTEM_*` vivos | 15 ficheiros `FRONTEND_*` |
| Template catalog expansion trilho | `TEMPLATE_CATALOG.md` (já canónico) | `TEMPLATE_CATALOG_EXPANSION_*` |
| STRIDE plan/report/test | `STRIDE_GENERICITY_REDUCTION_DECISION.md` (anexo) | `STRIDE_GENERICITY_REDUCTION_{PLAN,REPORT,TEST_STRATEGY}.md` |
| Inovação diff + fecho RC | `THREAT_MODEL_DIFF.md` (secção histórico) | `INNOVATION_PHASE_*.md` |
| Rodada qualidade + staging commits | `RELEASE_ENGINEERING_CHECKLIST.md` | `ENGINEERING_QUALITY_*`, `QUALITY_COMMIT_PLAN.md` |
| Fechos / rounds só histórico CHANGELOG | — | `PROJECT_CLOSURE_*`, `FINAL_*CLOSEOUT*`, `ROUND2_*`, `ADVANCED_*`, `FINAL_RELEASE_GATE*`, `FINAL_EXECUTIVE_*`, `CONSOLIDATION_ELITE_*` |

### 4.2 **Preservar** (com razão)

- `REMEDIATION_BACKLOG.md` — feature do produto.
- `FULL_PROJECT_CLEAN_ARCHITECTURE_AUDIT.md` — auditoria longa única.
- `STRIDE_GENERICITY_REDUCTION_DECISION.md` — decisão técnica viva + anexo.
- `E2E_GATE_DECISION.md`, `SONAR_DECISION_REPORT.md`, `RESIDUAL_RISK_REGISTER.md` — decisões curtas úteis.
- Toda a árvore `tests/`, `scripts/` com referências reais, `contracts/`.

### 4.3 Fora do escopo desta rodada

- Reescrita de conteúdo histórico dentro de `CHANGELOG.md` (entradas antigas mantêm nomes de ficheiros removidos como registo temporal).
- Playwright E2E completo local (validação em CI / ambiente dedicado).
- Refactor de código além do estritamente necessário para gates.

---

## 5. Plano de execução (realizado)

Ver `PROJECT_HYGIENE_ROUND2_EXECUTION_LOG.md`.

---

## 6. Riscos

- **Links externos** a paths removidos (fora do repo).
- **Histórico Git** ainda contém ficheiros apagados — recuperáveis por commit.
- **Interpretação:** alguns fechos listavam artefactos em `artifacts/` datados — hoje `.gitignore`; valor era sobretudo *timestamp* operacional.

---

## 7. Lista segura de retenção (não exaustiva)

`README.md`, `SECURITY.md`, `CONTRIBUTING.md`, `docs/README.md`, `ARCHITECTURE.md`, `API.md`, `CLI.md`, `DEFINITION_OF_DONE.md`, `RELEASE_ENGINEERING_CHECKLIST.md`, `LAUNCH_CHECKLIST.md`, `KNOWN_LIMITATIONS.md`, `adr/*`, `packages/*`, `apps/*`, `tests/*`, `scripts/*`, `examples/*`, `fixtures/*`.

---

## 8. Decisão final (rodada 2)

**Executar** consolidação documental agressiva conforme log; **manter** um único backlog de engenharia canónico; **substituir** relatórios de execução por um único `CI_AND_SECURITY_EVIDENCE.md`; **eliminar** trilhos UI redundantes em favor de histórico de uma página.
