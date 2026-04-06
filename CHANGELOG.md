# Changelog

Todas as mudanças relevantes neste projeto serão documentadas aqui.

Este arquivo segue o estilo de [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e versionamento semântico quando aplicável.

## [Unreleased]

### Added

### Changed

### Fixed

<!-- Compare links: atualizar com URL do repositório remoto após primeiro push de tag. -->

## [6.0.0] — 2026-04-06

Release **v6.0** (contratos TS alinhados ao motor, diff semântico v1.2, E2E crítico, SonarCloud + cobertura, anti-patterns e repo scan reforçados, relatório premium e exportadores multi-canal).

### Added

- Contrato TS forte: `AnalysisDiff`, `ThreatDeltaSummary`, `ComparisonMeta` (`semantic_structural_refs`, `interpretation_disclaimer`), `AnalysisResult` com `structural_findings` / `trust_boundary_findings`; testes `tests/test_comparison_ts_contract_alignment.py`.
- Diff semântico v1.2: contagens estruturais em `semantic_diff_sections.structural_change_summary`, refs `semantic_structural_refs`, disclaimer explícito; `comparison_contract_version` 1.2.
- E2E crítico: `apps/web/e2e/journeys.spec.ts`, `e2e/cockpit.spec.ts`; script `npm run e2e:critical`.
- Repo scan: deteções reforçadas (multer/express.file/busboy, sessão, child_process/fork, rotas debug), `modeling_hints` e `import_signals_corpus_snippets`; `repo_ast_optional`; tags `import:signal:` no corpus de anti-patterns.
- Documentação: `docs/FINAL_CLOSEOUT_ROUND.md`, `audit-gpt.md`, pacote de auditoria (`docs/BRUTAL_*.md`, `docs/FULL_PROJECT_*.md`, `docs/CONSOLIDATION_ELITE_ROUND.md`).
- Workflow `sonarcloud.yml`: `pytest` com cobertura (`coverage.xml`) e scan SonarCloud (`SONAR_TOKEN`, variável `SONAR_ORGANIZATION`).
- `exportArtifactHelpers.ts` (extensão/MIME de export) e `sonar-project.properties` alargado (`gitpage`, `examples`, `sonar.tests`, `coverage.xml`, exclusões de artefactos/fixtures).
- `pytest-cov` e `[tool.coverage.run]` para cobertura em `packages` + `apps`.
- Gate decisivo GO/NO-GO de uma página para publicação (`docs/GO_NO_GO_v0.1.0.md`).
- Paridade multi-canal: `semantic_insights` fundidos em `key_insights` na comparação; secção narrativa no Markdown de diff; diff semântico entre análises no report premium com baseline; CLI `diff` texto com blocos semânticos.
- Anti-patterns: catálogo expandido (SaaS, webhooks, API, e-commerce, admin, upload), `mitigating_keywords`, pré-requisitos estruturais mínimos, `confidence_hint` e `detection_sources` nos hits; `wizard_audit_models`.
- Teste de contrato `tests/test_analysis_ts_contract_alignment.py` (campos `AnalysisResult` vs SPA).
- UI: rastreio colapsável da modelação guiada no cockpit; labels de qualidade em português.
- `.gitignore`: exclusões para artefactos de cobertura/Sonar quando aplicável.

### Changed

- Anti-patterns: gates híbridos (component id, kinds gateway, cross-boundary flows, min flows upload) sem abandonar `missing_any_of`; cópia local de `_cross_boundary_flow_ids` para evitar import circular.
- Benchmark golden: `min_model_completeness_score` 37 nos quatro templates principais (`benchmark_expectations_v1.json`).
- Cockpit: faixa executiva com ligação a diff/export; página diff com painéis semânticos e bloco de refs estruturais.
- `benchmark_metrics`: densidade de anti-patterns normalizada por `/8` (catálogo maior).
- Templates `saas-web` e `webhook-ingestion` passam a expor `template_semantic_profile` dedicado.

### Fixed

- `ExportPage`: `replaceAll` e regex de nome de ficheiro PDF (`[^\w-]+`) para regras SonarJS.
- `anti_pattern_library`: descrição de `require_any_component_kinds` em `Field(...)` como string multilinha (reduz risco de falha CPD no scan Sonar).

## [5.0.0] — 2026-04-03

Release **v5.0** (cockpit de decisão na análise, sinais adaptativos do wizard, comparação semântica, anti-patterns, métricas de benchmark e varredura de repositório para importação de artefatos).

### Added

- UI: `DecisionCockpit`, `ModelQualityStrip`, constantes de wizard adaptativo (`adaptiveWizard`).
- Engine: biblioteca de anti-patterns, métricas de benchmark, comparação semântica de threat models, sinais de wizard e dados de referência.
- Importação: `repo_scan` para varredura de repositório (`packages/artifact-import`).
- Documentação: `docs/ADVANCED_PRODUCT_ROUND.md`; testes e fixtures de benchmark e análise.

### Changed

- CLI, páginas de análise/diff/review/wizard, `SessionContext`, tipos de documento/API e motor de análise alinhados ao conjunto v5.0.

## [4.0.0] — 2026-04-02

Release **v4.0** (pacote de qualidade de modelagem, relatórios premium, heurísticas compostas e completude metodológica).

### Added

- Pacote `report-premium`, relatórios premium e documentação (`docs/PREMIUM_REPORTS.md`).
- Modelos de qualidade de modelagem e pré-checagem (`docs/MODELING_QUALITY.md`, `model_quality_precheck`, `methodology_fit_matrix`).
- Heurísticas compostas, completude metodológica NIST e gate de recomendações.

### Changed

- API, CLI, UI e templates de industry packs alinhados ao conjunto de funcionalidades v4.0.

## [0.1.0] — 2026-04-01

Primeira release pública incremental coordenada (**App Suite Modeling**), com escopo congelado e documentação de maturidade por área.

### Added

- Camada inicial de framework mappings (OWASP TM, OWASP ASVS, NIST CSF, ISO 27001).
- Exportadores para JSON, Markdown e Mermaid.
- API FastAPI (`/v1/models`, `/v1/templates`, `/v1/exports`, diff, compare, analyses).
- UI web com fluxo guiado (criar, revisar, analisar, exportar).
- Branding **App Suite Modeling** com guia de identidade visual.
- PASTA fase 2 incremental (heurísticas risk-centric + insights estruturados).
- PLOT4ai fase 2 incremental (subdomínios AI/LLM + calibração com fixtures e casos negativos).
- Smoke suite de release candidate (`tests/test_smoke_release_candidate.py`).
- Documentação de release: checklist, smoke validation, choose methodology e notas RC históricas.
- Scripts UI portáteis para CI/Windows: `ci:build:portable`.
- Smoke E2E mínimo da UI (Playwright, headless).
- Playbook de publicação (`docs/PUBLISH_PLAYBOOK.md`).
- Checklist final de lançamento (`docs/LAUNCH_CHECKLIST.md`).
- Congelamento de escopo e maturidade (`docs/RELEASE_SCOPE_FREEZE.md`).
- Limitações conhecidas consolidadas (`docs/KNOWN_LIMITATIONS.md`).
- Relatório de validação da rodada final (`docs/VALIDATION_REPORT_v0.1.0.md`).
- Guia de versionamento e tags (`docs/VERSIONING_AND_TAGS.md`).
- Verificação automática mínima de links internos da documentação (`tests/test_docs_links.py`).

### Changed

- Documentação principal alinhada ao estado real do produto.
- `otm --version` mostra a versão instalada do pacote.
- Mensagens de erro da CLI padronizadas com falha, causa e próximo passo.
- CI com matriz web Linux/Windows e caminho de build portátil no Windows.
- `analysis_markdown` com resumo mais acionável, priorização de riscos e próximos passos.
- CI com job adicional de smoke E2E da UI.
