# Changelog

Todas as mudanças relevantes neste projeto serão documentadas aqui.

Este arquivo segue o estilo de [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e versionamento semântico quando aplicável.

## [Unreleased]

### Added

### Changed

### Fixed

- **`gitpage/package-lock.json`** regenerado com **npm 10.x** (alinhado ao **Node 20** no GitHub Actions). Locks gerados com **npm 11** faziam `npm ci` falhar no deploy Pages (pacotes **`@emnapi/*`** em falta no lock; mensagem no UI pode parecer “openapi”).
- **`apps/web`:** **`i18next` ^26.0.3** com **`react-i18next` ^17** (peer `i18next@>=26.0.1`); **`package-lock.json`** atualizado com **npm 10.x** para **`npm ci`** no CI não falhar com **ERESOLVE** (npm 10 é mais estrito que npm 11 neste par).
- CI: **`aquasecurity/trivy-action`** atualizado para **0.35.0** (advisory / Dependabot security job deixava de aplicar patch e falhava com `security_update_not_needed` com **0.28.0**).
- **`deploy-gitpage.yml`:** passo **`actions/configure-pages@v5`** antes de `upload-pages-artifact` (requisito do fluxo GitHub Pages).
- **Dependabot:** removida duplicata de entrada **`npm` / `gitpage`**; adicionado **`package-ecosystem: github-actions`** para atualizações semanais de actions.

### Removed

<!-- Compare links: atualizar com URL do repositório remoto após primeiro push de tag. -->

## [7.2.0] — 2026-04-02

Release **v7.2** — perímetro opcional da API (rate limit, API key), hardening do front-end e da pipeline CI, stack web React 19 / Vite 8, grupos Dependabot para Vite, alinhamento **gitpage** com Vite 8, correções de qualidade (mypy, Ruff, artefactos) e documentação de segurança.

### Added

- `.gitleaksignore` — exclusão de `.venv/`, `node_modules/` e artefactos de build para `gitleaks detect --no-git` sem falsos positivos locais.
- Vitest: `apps/web/src/utils/diagramSanitize.test.ts` (etiquetas do diagrama: remoção de HTML, whitespace, truncagem).
- API: **`slowapi`** (rate limit: `OTM_RATE_LIMIT`, `OTM_RATE_LIMIT_DISABLED`; defeito **120/minute** em staging/produção) e middleware **`OptionalApiKeyMiddleware`** quando **`OTM_API_KEY`** está definida (`X-OTM-API-Key` / `Authorization: Bearer` em `/v1/*`). Ficheiros `otm_api.perimeter_settings`, `otm_api.middleware_api_key`.
- CI: jobs **Semgrep** (`p/python`, `p/typescript`, `p/javascript`, `p/react`) e **Trivy** (imagem Docker da API); gate **`npm audit --audit-level=moderate`** no job `web`.
- Testes `tests/test_api.py` para API key; E2E híbrido com **`OTM_RATE_LIMIT_DISABLED=1`** no uvicorn (`playwright.hybrid.config.ts`).
- Frontend: **`public/_headers`** (CSP + cabeçalhos para hosts estáticos), **`public/theme-init.js`** (tema sem script inline), endurecimento em **`vite.config.ts`** (`server` / `preview` headers).
- **`.semgrepignore`**; política **`docs/SEMGREP_POLICY.md`**; guia **`docs/SECURITY_HEADERS.md`**; **`docs/PRE_COMMIT.md`**; **`.pre-commit-config.yaml`** (Ruff + mypy parcial).
- Workflow **`deploy-gitpage.yml`** (build e deploy do site em `gitpage/` para GitHub Pages).

### Changed

- CI (`.github/workflows/ci.yml`): gate **`ruff format --check`** no job Python, além de `ruff check`; job **Bandit** (`-ll`, medium+) sobre `packages/` e `apps/`; **Mypy monorepo** (todos os pacotes Python principais + CLI); jobs **semgrep** e **trivy-image**.
- `pyproject.toml` extra `dev`: dependência **`bandit>=1.7`** para SAST reprodutível; extra `api`: **`slowapi>=0.1.9`**.
- Python: formatação Ruff aplicada em massa (`packages/`, `apps/`, `tests/`) para alinhar com o novo gate.
- API: respostas de validação usam `status.HTTP_422_UNPROCESSABLE_CONTENT` (Starlette/FastAPI) em `otm_api.errors` e `otm_api.routers._errors`, eliminando `DeprecationWarning` de `HTTP_422_UNPROCESSABLE_ENTITY`.
- `docs/DEPLOYMENT_INVARIANTS.md`: secção **API sem autenticação integrada** + variáveis **`OTM_API_KEY`**, **`OTM_RATE_LIMIT`**, **`OTM_RATE_LIMIT_DISABLED`**.
- `pyproject.toml`: comentário no extra `api` sobre **SQLAlchemy** reservado a persistência pós-MVP (sem uso no código da API atual).
- `docs/CI_AND_SECURITY_EVIDENCE.md`: Ruff/Bandit, **Mypy monorepo**, Semgrep, Trivy, npm audit moderate.
- `docs/API.md`: secção **Perímetro opcional**; `docs/KNOWN_LIMITATIONS.md`: **`OTM_API_KEY`** opcional.
- **Mypy:** correcções transversais (tipos `StrideCategory` em heurísticas PLOT4ai, variáveis de loop em Markdown premium/diff export, `ai_import_corpus`, `document_json`, etc.); `otm_artifact_import.builders` com `type: ignore[call-arg]` documentado (falso positivo pydantic/mypy).
- **Web (`apps/web`):** **React ^19.2**, **Vite ^8**, `@vitejs/plugin-react` ^6, **Vitest ^3.2**; Dependabot agrupa `vite` + `@vitejs/plugin-react` para evitar **ERESOLVE** no `npm ci` (PRs separados incompatíveis).
- **`gitpage/` (site estático):** **Vite ^8** e `@vitejs/plugin-react` ^6 (mesma regra de peers); Dependabot semanal em `/gitpage` com grupo `vite-ecosystem`; `vite.config.ts`: `manualChunks` em forma de **função** (Rolldown rejeita o mapa objeto).
- CI **Semgrep**: configs adicionais **`p/javascript`** e **`p/react`**.

### Fixed

- `apps/web`: **Tailwind CSS** fixado em `3.4.19` (evita resolução para v4, que exige `@tailwindcss/postcss` e quebrava `postcss.config.js` + build Vite/E2E). Dependabot: ignorar **major** em `tailwindcss` até migração explícita para v4.
- `apps/web`: **TypeScript** restrito a `~5.9.3` — `openapi-typescript@7.6.1` exige peer `typescript@^5.x`; TS 6 faz `npm ci` falhar com **ERESOLVE**. Dependabot: ignorar **major** em `typescript` até `openapi-typescript` suportar TS 6 (ou troca de ferramenta).
- CI Dependabot: PRs que atualizavam só **Vite 8** ou só **`@vitejs/plugin-react` 6** quebravam `npm ci` (**ERESOLVE** entre peers). **Vite 8** e **plugin-react 6** passam a subir em conjunto no `apps/web`; grupo Dependabot `vite-ecosystem`. **`gitpage/`:** Vite 8 + plugin-react 6 alinhados para o mesmo motivo.

### Removed

## [7.1.0] — 2026-04-08

Release **v7.1** (i18n pt-BR/en, exports e premium localizados, CLI modular, observabilidade e CORS na API, CI com mypy/pip-audit/npm audit/E2E crítico, diff semântico v1.5, higiene documental).

### Removed

- Higiene **round 3** (documentação): removido o pacote disperso `docs/I18N_*.md` (substituído por **`docs/I18N.md`**). Relatórios `docs/PROJECT_HYGIENE_ROUND3_*`.

- Higiene de repositório (release readiness): removido arquivo versionado `docs/archive/legacy-md-2026-03-24/` (29 ficheiros Markdown já marcados como legados e sem referências no código, CI ou documentação viva). Rastreio no histórico Git; sumário consolidado na round 2 (`docs/PROJECT_HYGIENE_ROUND2_*`).

- Higiene **round 2** (documentação): removidos dezenas de Markdown redundantes ou puramente operacionais (pacotes `BRUTAL_*` paralelos, trilhos UI plano/validação/handoff, relatórios de execução CI dispersos, fechos/rounds históricos, ficheiros da higiene round 1). Conteúdo durável fundido em `docs/FULL_PROJECT_REMEDIATION_BACKLOG.md`, `docs/FULL_PROJECT_REMEDIATION_PLAN.md`, `docs/FULL_PROJECT_QUALITY_SCORECARD.md`, `docs/CI_AND_SECURITY_EVIDENCE.md`, `docs/EXPLAINABILITY.md`, `docs/THREAT_MODEL_DIFF.md`, `docs/STRIDE_GENERICITY_REDUCTION_DECISION.md`, `docs/GITHUB_README_AND_METADATA.md`, `docs/FRONTEND_UI_ROLLOUT_HISTORY.md`. Rastreio em `docs/PROJECT_HYGIENE_ROUND2_*`.

### Added

- Documentação consolidada (higiene round 2): `docs/CI_AND_SECURITY_EVIDENCE.md`, `docs/GITHUB_README_AND_METADATA.md`, `docs/FRONTEND_UI_ROLLOUT_HISTORY.md`; relatórios `docs/PROJECT_HYGIENE_ROUND2_AUDIT_REPORT.md`, `docs/PROJECT_HYGIENE_ROUND2_EXECUTION_LOG.md`, `docs/PROJECT_HYGIENE_ROUND2_FINAL_SUMMARY.md`.
- Documentação consolidada (higiene round 3): `docs/I18N.md`; relatórios `docs/PROJECT_HYGIENE_ROUND3_AUDIT_REPORT.md`, `docs/PROJECT_HYGIENE_ROUND3_EXECUTION_LOG.md`, `docs/PROJECT_HYGIENE_ROUND3_FINAL_SUMMARY.md`.

- Web (`apps/web`): internacionalização **pt-BR** / **en** com **i18next** + **react-i18next**; `LanguageSwitcher` no header; locales em `src/i18n/locales/`; persistência `otm.web.locale`; testes Vitest (`localePolicy`); E2E `e2e/i18n.spec.ts`; `playwright.config.ts` com `locale: "pt-BR"` para estabilizar cópia PT nos testes.
- i18n de **artefactos**: `POST /v1/exports` com `locale` opcional validado (`pt-BR` \| `en`); exportadores Markdown com rótulos bilíngues; PDF no cliente (`generateReportPdf`) com chaves `artifactPdf.*`; resolução centralizada em `exportArtifactLocale.ts`; `ExportPage` com `export-artifact-locale`; testes `tests/test_export_locale.py`, `tests/test_api.py::test_export_document_markdown_locale_en`, Vitest `exportArtifactLocale.test.ts`.
- i18n **report premium** (Fase 3): `PremiumReportPayload.locale`, `report_i18n.py`, `i18n_locale.py`, builder/render MD/HTML bilíngues; `POST /v1/reports/premium` + `PremiumReportBody.locale`; web `fetchPremiumReport({ locale })`; CLI `otm report --locale`; testes `tests/test_premium_i18n_locale.py`, `test_premium_report.py`, `test_api.py::test_reports_premium_markdown_locale_en`.
- Documentação i18n: **`docs/I18N.md`** (canónico: política, API/exports, premium, limitações, glossário, verificação); `docs/PREMIUM_REPORTS.md` atualizado. *(Nota: ficheiros `docs/I18N_*.md` dispersos foram fundidos neste documento na higiene round 3.)*
- Auditoria final i18n (implementação): normalização única export/premium + variantes BCP47 em `export_locale.py`; placeholders i18n em `RunEngineCard`, `ReviewPage`, `WizardPage`. Evidência editorial consolidada em `docs/I18N.md` secção 9.

- CLI modular: `apps/cli/otm_cli/commands/`, `application/`, `shared/`; `cli.py` só bootstrap Typer; testes `tests/test_cli_application.py`.
- API: observabilidade JSON (`request_id`, duração, eventos HTTP) em `otm_api.observability`; CORS por `OTM_ENV` / `OTM_CORS_ORIGINS` em `otm_api.cors_settings`.
- CI: job **mypy** (core-schema + API), **pip-audit** no ambiente do projeto, **npm audit --audit-level=critical** em `apps/web`, job **web-e2e-critical** (`e2e:critical`); Dependabot pip + npm.
- Relatórios e gates DevSecOps: evidência **consolidada** em [`docs/CI_AND_SECURITY_EVIDENCE.md`](docs/CI_AND_SECURITY_EVIDENCE.md); [`docs/DEPLOYMENT_INVARIANTS.md`](docs/DEPLOYMENT_INVARIANTS.md); [`docs/E2E_GATE_DECISION.md`](docs/E2E_GATE_DECISION.md); [`docs/SONAR_DECISION_REPORT.md`](docs/SONAR_DECISION_REPORT.md). *(Relatórios pontuais `*_EXECUTION_REPORT.md` com o mesmo tema foram fundidos em `CI_AND_SECURITY_EVIDENCE.md` na higiene docs.)*
- Documentação de fecho: `docs/RELEASE_ENGINEERING_CHECKLIST.md` (gates de release), `docs/DEFINITION_OF_DONE.md`, `docs/ENGINEERING_CLOSEOUT_SCOPE.md`; índice e alinhamento de versão em `docs/README.md`, `RELEASE_SCOPE_FREEZE.md`, `LAUNCH_CHECKLIST.md`, `GO_NO_GO_v0.1.0.md`, `KNOWN_LIMITATIONS.md`.

- Diff semântico **v1.5**: `anchoring_rationale` em cada ligação; `inference_strength` **medium** quando ≥2 tokens lexicais coincidem; `comparison_contract_version` / `semantic_insights_version` **1.5**.
- `ComparisonResultMeta`: raiz **`extra=forbid`** + campo **`extensions`** para evolução controlada (OpenAPI sem `additionalProperties` soltas na raiz).
- Repo scan Python: rotas `@app/@router.*`, `UploadFile`/multipart, `Depends`/OAuth2/sessão, clientes **httpx/requests/aiohttp**, `/admin`/`/debug`; `modeling_hints` alinhados (`python_upload`, `python_external_http`, `python_auth_layer`, `python_route`).
- `scripts/check_hybrid_prereqs.py`; `npm run e2e:hybrid:check`; `e2e:hybrid` corre a verificação antes do Playwright.

### Changed

- Web: páginas e blocos de análise (incl. `ExportPage`, `HistoryPage`, `TemplatesPage`, `DiffPage`) e componentes associados passam a usar `t()` / `Trans` em vez de strings fixas na UI.
- Removido `sonar-project.properties` órfão (sem job Sonar no CI); ver `docs/SONAR_DECISION_REPORT.md`.
- UI diff, Markdown e CLI mostram racional de ancoragem (v1.5).
- Documentação: `docs/THREAT_MODEL_DIFF.md`, `docs/CONTRACTS_CI_HYBRID.md` (fluxo híbrido + `meta` fechado).

### Fixed

- API: ordem de imports em `apps/api/otm_api/observability.py` (Ruff **I001**) para o gate `ruff check` passar.

## [7.0.0] — 2026-04-07

Release **v7.0** (OpenAPI como contrato vivo, diff semântico v1.4, E2E híbrido API+UI, goldens HTTP, verificação anti-stale do contrato no CI).

### Added

- Gate **anti-stale** OpenAPI: `scripts/verify_openapi_up_to_date.py`, `npm run contracts:verify` (apps/web); passo no CI Python.
- Goldens HTTP semânticos: `tests/test_http_response_goldens.py` + `tests/fixtures/golden/http_api_semantic_expectations.json`.
- E2E **híbrido**: `playwright.hybrid.config.ts`, `e2e/hybrid.spec.ts`, `npm run e2e:hybrid`, job CI `hybrid-e2e`.
- `e2e/fixtures/minimal-document.json` (documento canónico para testes híbridos).
- Documentação: `docs/CONTRACTS_CI_HYBRID.md`, `docs/ROUND2_INTEGRATED_CLOSEOUT.md`. *(Nota editorial 2026-04: `ROUND2_INTEGRATED_CLOSEOUT.md` foi removido na higiene docs; ver `docs/THREAT_MODEL_DIFF.md` e `docs/CI_AND_SECURITY_EVIDENCE.md`.)*
- OpenAPI como fonte de tipos TS: `contracts/openapi.json`, `scripts/export_openapi.py`, `openapi-typescript`, `apps/web/src/types/generated/openapi.d.ts`, scripts `contracts:sync` no pacote web.
- `response_model` explícito em `POST /v1/models/analyze` e `/compare` para esquemas reais no OpenAPI.
- Schemas OpenAPI **`ComparisonResultMeta`**, **`SemanticInterpretationLinkModel`**, **`SemanticStructuralRefModel`**, **`SemanticDiffSectionsModel`** — `meta` tipado no contrato exportado (com `additionalProperties` para extensões).
- Diff semântico **v1.4**: `lexical_token_overlap` + `entity_topic_correlation`; `link_kind`, `inference_strength` `low`, `shared_tokens`; `change_category` nas refs; `comparison_contract_version` **1.4**; UI, Markdown e CLI alinhados.
- Anti-patterns **structural_primary** (admin, upload+`supports_file_upload`, API gateway, e-commerce) com `mitigating_keywords` / `missing_any_of` como filtro secundário.
- Repo scan: ficheiros `.py`, deteção FastAPI/Flask/ASGI, `stack_hint` nas inferências, `detected_stacks`, hint de boundary para FastAPI.
- Testes: `tests/test_openapi_contract_file.py`, `test_structural_primary_gateway_cross_boundary_without_rate_keywords`, `test_scan_detects_python_fastapi_signals`.
- E2E: `e2e/import.spec.ts` (import mock + revisão); jornada diff com `semantic_interpretation_links`.

### Changed

- `response_model` em **precheck**, **diff estrutural**, **analyses/diff**, **remediation/backlog** (JSON), **exports**, **imports**; premium documentado por media type.
- `ThreatModelComparisonResult.meta` no motor: `ComparisonResultMeta` Pydantic (serialização estável); consumidores Markdown/CLI usam atributos tipados.
- `apps/web/src/types/api.ts`: tipos de motor reexportados a partir do OpenAPI gerado; `ComparisonMeta` / `SemanticInterpretationLink` alinhados ao diff **v1.4**; endurecimento pontual (`AnalysisResult`, `ThreatModelComparisonResult`) para o SPA.
- Benchmark golden: `min_model_completeness_score` **38** nos quatro templates wave principais.
- Microcopy da faixa executiva no cockpit (costura compare/export).
- CI: remoção do workflow SonarCloud em favor de SonarQube local documentado; `ci.yml` com verificação OpenAPI e job híbrido.

### Fixed

- Componentes TS: optional chaining / defaults onde o OpenAPI marca opcional mas o UI assume listas.
- CI (Ubuntu): instalação de `libcairo2-dev` e `pkg-config` antes do `pip install`, para compilar `pycairo` (cadeia `xhtml2pdf` → `svglib`).

## [6.0.0] — 2026-04-06

Release **v6.0** (contratos TS alinhados ao motor, diff semântico v1.2, E2E crítico, SonarQube local + cobertura pytest, anti-patterns e repo scan reforçados, relatório premium e exportadores multi-canal).

### Added

- Contrato TS forte: `AnalysisDiff`, `ThreatDeltaSummary`, `ComparisonMeta` (`semantic_structural_refs`, `interpretation_disclaimer`), `AnalysisResult` com `structural_findings` / `trust_boundary_findings`; testes `tests/test_comparison_ts_contract_alignment.py`.
- Diff semântico v1.2: contagens estruturais em `semantic_diff_sections.structural_change_summary`, refs `semantic_structural_refs`, disclaimer explícito; `comparison_contract_version` 1.2.
- E2E crítico: `apps/web/e2e/journeys.spec.ts`, `e2e/cockpit.spec.ts`; script `npm run e2e:critical`.
- Repo scan: deteções reforçadas (multer/express.file/busboy, sessão, child_process/fork, rotas debug), `modeling_hints` e `import_signals_corpus_snippets`; `repo_ast_optional`; tags `import:signal:` no corpus de anti-patterns.
- Documentação: `docs/FINAL_CLOSEOUT_ROUND.md`, limitações do produto (`docs/KNOWN_LIMITATIONS.md`; em comunicações antigas também `audit-gpt.md`), pacote de auditoria (`docs/BRUTAL_*.md`, `docs/FULL_PROJECT_*.md`, `docs/CONSOLIDATION_ELITE_ROUND.md`). *(Nota editorial 2026-04: vários destes ficheiros foram fundidos ou removidos; estado canónico em `docs/README.md`, `docs/FULL_PROJECT_CLEAN_ARCHITECTURE_AUDIT.md`, `docs/FULL_PROJECT_REMEDIATION_BACKLOG.md`, `docs/CI_AND_SECURITY_EVIDENCE.md`.)*
- `exportArtifactHelpers.ts` (extensão/MIME de export) e `sonar-project.properties` alargado para SonarQube local (`gitpage`, `examples`, `sonar.tests`, `coverage.xml`, exclusões de artefactos/fixtures).
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
- Documentação: `docs/ADVANCED_PRODUCT_ROUND.md`; testes e fixtures de benchmark e análise. *(Nota editorial 2026-04: `ADVANCED_PRODUCT_ROUND.md` removido na higiene docs; conteúdo de produto coberto por `docs/README.md`, `docs/EXPLAINABILITY.md`, `docs/MODELING_QUALITY.md`.)*

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
