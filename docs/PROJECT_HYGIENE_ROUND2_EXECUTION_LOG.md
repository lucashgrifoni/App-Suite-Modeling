# Log de execução — higiene rodada 2

**Data:** 2026-04-06

---

## 1. Ficheiros removidos do índice Git (`git rm`)

**Total: 38** (exclui `docs/archive/` da round 1)

1. `docs/ADVANCED_PRODUCT_ROUND.md`  
2. `docs/BRUTAL_AUDIT_REPORT.md`  
3. `docs/BRUTAL_REMEDIATION_BACKLOG.md`  
4. `docs/BRUTAL_REMEDIATION_PLAN.md`  
5. `docs/BRUTAL_SCORECARD.md`  
6. `docs/CONSOLIDATION_ELITE_ROUND.md`  
7. `docs/ENGINEERING_QUALITY_ROUND_REPORT.md`  
8. `docs/FINAL_CLOSEOUT_ROUND.md`  
9. `docs/FINAL_EXECUTIVE_READINESS_REPORT.md`  
10. `docs/FINAL_RELEASE_GATE_DECISION.md`  
11. `docs/FRONTEND_FINAL_RELEASE_ASSETS_HANDOFF.md`  
12. `docs/FRONTEND_FINAL_RELEASE_ASSETS_PLAN.md`  
13. `docs/FRONTEND_FINAL_RELEASE_ASSETS_VALIDATION.md`  
14. `docs/FRONTEND_MODERNIZATION_HANDOFF.md`  
15. `docs/FRONTEND_MODERNIZATION_PLAN.md`  
16. `docs/FRONTEND_MODERNIZATION_VALIDATION.md`  
17. `docs/FRONTEND_PHASE3_PRODUCT_POLISH_HANDOFF.md`  
18. `docs/FRONTEND_PHASE3_PRODUCT_POLISH_PLAN.md`  
19. `docs/FRONTEND_PHASE3_PRODUCT_POLISH_VALIDATION.md`  
20. `docs/FRONTEND_PHASE4_FEATURES_HANDOFF.md`  
21. `docs/FRONTEND_PHASE4_FEATURES_PLAN.md`  
22. `docs/FRONTEND_PHASE4_FEATURES_VALIDATION.md`  
23. `docs/FRONTEND_REFINEMENT_PHASE2_HANDOFF.md`  
24. `docs/FRONTEND_REFINEMENT_PHASE2_PLAN.md`  
25. `docs/FRONTEND_REFINEMENT_PHASE2_VALIDATION.md`  
26. `docs/INNOVATION_PHASE_1_THREAT_MODEL_DIFF.md`  
27. `docs/INNOVATION_PHASE_FINAL_INTEGRATION_RC.md`  
28. `docs/PROJECT_CLOSURE_SUMMARY.md`  
29. `docs/QUALITY_COMMIT_PLAN.md`  
30. `docs/README_RELEASE_HANDOFF.md`  
31. `docs/README_RELEASE_VALIDATION.md`  
32. `docs/ROUND2_INTEGRATED_CLOSEOUT.md`  
33. `docs/STRIDE_GENERICITY_REDUCTION_PLAN.md`  
34. `docs/STRIDE_GENERICITY_REDUCTION_REPORT.md`  
35. `docs/STRIDE_GENERICITY_REDUCTION_TEST_STRATEGY.md`  
36. `docs/TEMPLATE_CATALOG_EXPANSION_HANDOFF.md`  
37. `docs/TEMPLATE_CATALOG_EXPANSION_PLAN.md`  
38. `docs/TEMPLATE_CATALOG_EXPANSION_VALIDATION.md`  

**Contagem:** **38** paths em `docs/` removidos do índice Git nesta consolidação (lista `git status` sem `docs/archive/`).

---

## 2. Ficheiros apagados do working tree (não rastreados pelo Git)

**Total: 8** — existiam como `??` localmente; removidos para alinhar ao estado consolidado.

- `docs/PROJECT_HYGIENE_AUDIT_REPORT.md`  
- `docs/PROJECT_HYGIENE_EXECUTION_LOG.md`  
- `docs/PROJECT_HYGIENE_FINAL_SUMMARY.md`  
- `docs/MYPY_CI_EXECUTION_REPORT.md`  
- `docs/SCA_EXECUTION_REPORT.md`  
- `docs/CLI_REFACTOR_EXECUTION_REPORT.md`  
- `docs/API_OBSERVABILITY_EXECUTION_REPORT.md`  
- `docs/API_PERIMETER_HARDENING_REPORT.md`  

---

## 3. Novos ficheiros

- `docs/CI_AND_SECURITY_EVIDENCE.md`  
- `docs/GITHUB_README_AND_METADATA.md`  
- `docs/FRONTEND_UI_ROLLOUT_HISTORY.md`  
- `docs/PROJECT_HYGIENE_ROUND2_AUDIT_REPORT.md`  
- `docs/PROJECT_HYGIENE_ROUND2_EXECUTION_LOG.md`  
- `docs/PROJECT_HYGIENE_ROUND2_FINAL_SUMMARY.md`  

---

## 4. Consolidações (conteúdo absorvido)

| Destino | Origem (removido) |
|---------|-------------------|
| `FULL_PROJECT_REMEDIATION_BACKLOG.md` | `BRUTAL_REMEDIATION_BACKLOG.md` (tabela mitigações + linhas BL-16–18) |
| `FULL_PROJECT_REMEDIATION_PLAN.md` | `BRUTAL_REMEDIATION_PLAN.md` (suplemento fases / caminho mínimo) |
| `FULL_PROJECT_QUALITY_SCORECARD.md` | `BRUTAL_SCORECARD.md` (nota histórica Staff/observabilidade) |
| `FULL_PROJECT_CLEAN_ARCHITECTURE_AUDIT.md` | `BRUTAL_AUDIT_REPORT.md` (nota de fusão no topo) |
| `CI_AND_SECURITY_EVIDENCE.md` | Cinco relatórios de execução + perímetro |
| `GITHUB_README_AND_METADATA.md` | `README_RELEASE_VALIDATION.md`, `README_RELEASE_HANDOFF.md` |
| `FRONTEND_UI_ROLLOUT_HISTORY.md` | 15× `FRONTEND_*` plan/val/handoff |
| `EXPLAINABILITY.md` | `CONSOLIDATION_ELITE_ROUND.md` (wizard trace, AST, E2E cockpit) |
| `THREAT_MODEL_DIFF.md` | `INNOVATION_PHASE_*.md` |
| `STRIDE_GENERICITY_REDUCTION_DECISION.md` | `STRIDE_GENERICITY_REDUCTION_{PLAN,REPORT,TEST_STRATEGY}.md` (anexo) |
| `RELEASE_ENGINEERING_CHECKLIST.md` | `ENGINEERING_QUALITY_ROUND_REPORT.md`, `QUALITY_COMMIT_PLAN.md` (secção histórico) |

---

## 5. Ficheiros editados (além dos anfitriões)

- `docs/README.md` — índice (novas entradas; removidas linhas README_RELEASE e INNOVATION_FINAL)  
- `docs/DEPLOYMENT_INVARIANTS.md` — link → `CI_AND_SECURITY_EVIDENCE.md`  
- `CHANGELOG.md` — [Unreleased] Added/Removed  

---

## 6. Preservados (explicitamente)

- `docs/REMEDIATION_BACKLOG.md` (produto)  
- `docs/STRIDE_GENERICITY_REDUCTION_DECISION.md` (decisão + anexo)  
- ADRs, checklists de release, limitações, contratos, código, testes, scripts  

---

## 7. Comentários / código morto

- Varredura `TODO|FIXME|HACK|XXX` em `py/ts/tsx`: **sem matches**.  
- Nenhuma remoção massiva de comentários (risco/benefício baixo nesta rodada).

---

## 8. Pendências

- Atualizar entradas **históricas** do `CHANGELOG.md` (opcional) com nota “nomes de ficheiros consolidados em …” — não feito para não reescrever histórico editorial.  
- `DeprecationWarning` FastAPI 422 (fora do escopo higiene docs).  
- E2E Playwright completo apenas em CI ou ambiente preparado.
