# Changelog

All notable changes to this project are documented here.

This project follows **Keep a Changelog** and **Semantic Versioning**.

---

## [Unreleased]

### Added
- **Threat traceability (CAPEC/CWE):** every generated STRIDE threat now carries a MITRE **CAPEC** attack-pattern and **CWE** weakness reference (e.g. Spoofing → `CAPEC-151` / `CWE-287`, Information Disclosure → `CAPEC-118` / `CWE-200`), alongside the existing OWASP ASVS / NIST CSF / ISO 27001 control references. Surfaced in `framework_ref_counts_by_catalog` and in the Markdown/JSON exports. Implemented data-driven via the STRIDE map — **no schema or OpenAPI contract change**. First step of the documented evolution plan ([docs/internal/reports/IMPROVEMENT_RESEARCH_2026-06.md](docs/internal/reports/IMPROVEMENT_RESEARCH_2026-06.md)).
- **SARIF export (`otm analyze --sarif-out <file>`):** suggested threats can now be written as **SARIF 2.1.0** — one result per active threat, grouped by a methodology+STRIDE rule, severity (`error`/`warning`/`note`) derived from the L×I score, and a rule `helpUri` linking to the threat's CWE/CAPEC reference — ready to upload to GitHub code scanning or any SARIF-aware pipeline. New `export_analysis_sarif` exporter; deterministic output. Contract-stable (CLI + exporter only). Second step of the evolution plan.
- **Open Threat Model (OTM) interoperability:** import IriusRisk **OTM 0.2.0** documents (`otm import otm <file>`) and export the canonical model to OTM (`otm export … --format otm`). Faithful structural round-trip (project / trust zones / components / dataflows / assets) with id sanitisation, referential-integrity guards, and component-`type`↔`kind` mapping — bridging App Suite Modeling with the OTM ecosystem (IriusRisk, StartLeft), the project's namesake format. New `otm_native` converter; CLI + converter only, no API/OpenAPI contract change. Third step of the evolution plan.
- **AI-lens traceability (OWASP LLM Top 10 2025 + MITRE ATLAS):** each PLOT4ai heuristic now carries standard AI-threat references — mapped per heuristic to the **OWASP Top 10 for LLM Applications 2025** (e.g. prompt-injection heuristics → `LLM01:2025`, RAG/embedding heuristics → `LLM08:2025`, agent tool-use → `LLM06:2025`, inference abuse → `LLM10:2025`) and, where a technique id is verified, to **MITRE ATLAS** (`AML.T0051` LLM Prompt Injection, `AML.T0024` Exfiltration via AI Inference API, `AML.T0034` Cost Harvesting). These are **additive** — a PLOT4ai threat keeps its STRIDE-category CAPEC/CWE references and gains the AI-specific ones — and surface in `framework_ref_counts_by_catalog` and the Markdown/JSON exports. Implemented data-driven via a new per-heuristic map (`ai_heuristic_framework_map.yaml`), reusing the same `framework_refs` mechanism as the CAPEC/CWE step — **no schema or OpenAPI contract change**. Fourth step of the evolution plan.
- **Report polish:** framework-reference aggregates now render friendly catalog labels — `capec` → *MITRE CAPEC*, `cwe` → *MITRE CWE*, `owasp_llm` → *OWASP LLM Top 10 (2025)*, `mitre_atlas` → *MITRE ATLAS* (previously the raw ids for the first two).

### Fixed
- **OTM import — malformed collection no longer crashes or silently empties the model.** `otm import otm` iterated the top-level OTM arrays with `for x in otm.get(key) or []`, which only substitutes *falsy* values. A present-but-non-array value therefore slipped through: a truthy scalar (`components: 5`, `dataflows: 3`) raised an uncaught `TypeError` that escaped every handler and printed a raw stack trace, while a string or mapping silently iterated its characters/keys and imported **zero** entries. Each of `trustZones` / `components` / `dataflows` / `assets` is now required to be an array when present, raising a `ValueError` the CLI renders as a friendly, actionable error (exit 1). Absent/`null`/empty still mean "no entries". Found by a pre-release deep review; regression tests added.
- **MITRE ATLAS reference name corrected.** The note for `AML.T0024` shipped the stale pre-rename name *"Exfiltration via ML Inference API"*. Per the canonical [`mitre-atlas/atlas-data`](https://github.com/mitre-atlas/atlas-data) (`dist/ATLAS.yaml`), MITRE renamed several techniques from *ML* to *AI*; the technique is **"Exfiltration via AI Inference API"**. The identifier itself was always correct. A test now pins the canonical names of all three referenced ATLAS techniques.
- **Security CI — a transient Snyk failure can no longer silently drop the Snyk gate.** The token probe added in `390c6fd` treated *any* non-zero `snyk auth` exit as "token unusable" and skipped the scan with a green job — so a Snyk outage, a `429` rate-limit, or a DNS/TLS blip would have quietly removed SAST+SCA coverage from a passing pipeline. The probe now distinguishes a genuine auth rejection (`SNYK-0005` / HTTP 401 → skip, with a Step Summary note) from every other failure (→ **fail closed and loud**, with an `::error::` annotation). Found by the same deep review.

### Maintenance
- **Dependencies:** refreshed `apps/web` and `gitpage` to the latest in-range versions (React 19.2.7, i18next 26.3.1, react-i18next 17.0.8, @playwright/test 1.61, Vitest, @vitejs/plugin-react 6.0.2, autoprefixer 10.5.0, lucide-react 0.577.0, and other in-range updates). `npm audit` remains **0** in both projects. Clears the open Dependabot npm PRs.
- **CI:** bumped pinned GitHub Actions to current SHAs — `step-security/harden-runner`, `actions/checkout`, and `github/codeql-action` (v4.36.2).
- **Repo hygiene:** `gitpage/.gitignore` now excludes the local `design-sync` tooling directories (scratch, ~43M of installed scripts/`node_modules`, and build bundles).

---

## [7.6.4] — 2026-06-18

### Security
- **API / industry-pack loader — path traversal (High, fixed):** `load_pack`, `load_template_yaml`, and `load_template_info` now reject any id that is not present in the embedded catalog *before* touching the filesystem. Previously an attacker-controlled `pack_id` (e.g. via unauthenticated `POST /v1/models/compare` with `run_analysis: true`) could contain `../` or an absolute path and make the loader read an arbitrary local `.yaml` file; combined with the validation-error echo below, the file's parsed contents were disclosed in the `422` body. Added an end-to-end regression test.
- **API — bounded validation-error echo:** domain `422` responses (`validate` / `precheck` / `analyze` / `diff` / `compare`) now truncate the echoed `input`/`ctx` to the same 256-character cap already applied to request-validation errors, so these errors can no longer reflect unbounded parsed content back to the client (closes the disclosure amplifier above and a ~1.6× response-amplification vector).
- **Exporters — generated-artifact injection hardening:** component and data-flow names are attacker-controllable model text. The Mermaid flowchart exporter now collapses line breaks and neutralizes the label-terminating `"`/`|`, so a crafted name can no longer inject extra Mermaid nodes/edges into the diagram source; the premium Markdown report escapes `|` and flattens line breaks in table cells, so a crafted name/threat title can no longer add columns or split a table row.
- **Web (`apps/web`):** bump `dompurify` `3.4.7 → 3.4.11` (transitive via `jspdf`), fixing three **Medium** DOMPurify advisories ([SNYK-JS-DOMPURIFY-17342528](https://security.snyk.io/vuln/SNYK-JS-DOMPURIFY-17342528), `-17344549`, `-17375136`); bump `vite → 8.0.16` (dev server / build tooling — **not** shipped in `dist/`) clearing [GHSA-fx2h-pf6j-xcff](https://github.com/advisories/GHSA-fx2h-pf6j-xcff) and [GHSA-v6wh-96g9-6wx3](https://github.com/advisories/GHSA-v6wh-96g9-6wx3); pin `js-yaml ≥ 4.2.0` via `overrides` to clear a **Medium** advisory reached through `openapi-typescript → @redocly/openapi-core`. `npm audit` now reports **0 vulnerabilities**.
- **GitHub Pages (`gitpage`):** bump `vite → 8.0.16`, clearing the same dev-tooling advisory; `npm audit` clean.

### CI
- **Security CI/CD** now degrades gracefully across contexts. A `preflight` job detects code-scanning availability (public repo or Advanced Security) and the Dependabot run context; SARIF upload, CodeQL, and Dependency Review are **skipped (not failed)** when unavailable, and Snyk/Gitleaks skip cleanly on Dependabot's read-only token. The scanners themselves remain hard gates on real findings. This clears the perpetual red on scheduled runs and Dependabot PRs without weakening detection, and re-activates full SARIF reporting automatically when the repository is public.

### Tests
- **Web UI:** added a Vitest component/hook/context/storage layer (jsdom + Testing Library) — 40 new unit tests covering `apiFetch` error mapping, analysis filters, browser-storage helpers, `ThemeContext`, `ToastContext`, `RiskScoreBar`, `StatusPill`, `EmptyState`, and `ErrorBoundary` (68 web unit tests total). Wired `vitest` into the GitHub CI/CD web job so unit tests now gate on every push and PR (previously only the build + Playwright E2E ran).
- **Python:** added the API error-truncation defensive branches (`errors.py` now 100%), a path-traversal security regression suite, and engine-defect regressions (PLOT4ai key-order seed independence; data-flow scoring). Suite is now **966 tests**.

### Fixed
- **Engine determinism (PLOT4ai):** `ai_system_context.heuristic_ids_by_layer` is now emitted in a stable canonical layer order. It was seeded from a `set(...)`, so the serialized key order varied with `PYTHONHASHSEED` across runs and broke byte-for-byte reproducibility of PLOT4ai analysis JSON (snapshots, signing, diffs). Values were already sorted — only the key order was affected.
- **Engine risk scoring (data flows):** an unencrypted data flow that does **not** cross a trust boundary is no longer double-counted. The STRIDE builder OR-ed "unencrypted" into the boundary-crossing signal while `risk_calc` already applied a dedicated encryption penalty, inflating such flows to L×I `5×5` (25, *critical*) instead of `4×4` (16, *high*). **Behavioral note:** this lowers scores and shifts the severity distribution for unencrypted internal flows (boundary-crossing and encrypted flows are unchanged); pinned analysis snapshots were regenerated accordingly.
- **Artifact import robustness:** importers no longer crash on valid-but-colliding or hostile input. `assemble_draft` now de-duplicates entities whose artifact-derived id collides — e.g. two Kubernetes resources of the same kind sharing a name across namespaces, a Terraform address duplicated across concatenated files, or names that collide after the slug length cap or against a reserved internal id — keeping the first and recording a reconciliation note in the draft's `unknowns`, instead of failing the entire draft with a schema "duplicate id" error (which previously surfaced as HTTP 400 / a CLI stack trace). OpenAPI/Swagger import additionally guards against non-string HTTP-method keys (YAML 1.1 `on`/`off`/numeric keys), which previously raised an `AttributeError` (HTTP 500).

---

## [7.6.3] — 2026-06-03

### Fixed
- **Web UI accessibility:** `Button` now renders an explicit keyboard-scoped `focus-visible` ring, matching the focus treatment of `Input` / `Select` / `Checkbox` (it previously relied only on the global outline, which the gradient variant could visually clip).
- **Web UI contrast:** lifted the dark-theme `--otm-text-subtle` token from `#5f7a6d` (~4.1:1) to `#789684` to clear WCAG AA (4.5:1) on the darkest surfaces, while keeping it clearly dimmer than `--otm-text-muted` (hierarchy preserved).

### CI
- Bumped `aquasecurity/trivy-action` to `v0.36.0` and `gitleaks/gitleaks-action` to `v3.0.0`, clearing the GitHub Actions Node 20 deprecation warnings (both now run on Node 24).

---

## [7.6.2] — 2026-06-03

### Security
- **Web (`apps/web`):** bump `react-router-dom` floor to `^7.14.2`; the lockfile now resolves `react-router` / `react-router-dom` `7.14.0 → 7.16.0`, fixing a **Critical** *Deserialization of Untrusted Data* advisory in `react-router` ([SNYK-JS-REACTROUTER-17137394](https://security.snyk.io/vuln/SNYK-JS-REACTROUTER-17137394)). Surfaced by the Snyk Open Source gate once code scanning re-enabled on the public repository; not yet present in the GitHub Advisory database at release time.

### Notes
- Supersedes `7.6.1`, whose security pipeline failed on the advisory above. `7.6.1` carries no contract change of its own; adopters should use `7.6.2`.

---

## [7.6.1] — 2026-06-03

### Summary
Maintenance and publication-readiness release. Clears the remaining CI quality gates from the 7.6.0 line, fixes cross-platform file-id handling in repository import, embeds real product screenshots in the README, and aligns the package version with the four post-7.6.0 commits. **No public CLI / API / UI contract change.**

### Fixed
- `otm import repo`: `_short_file_id` normalizes Windows backslash separators so generated component IDs are stable across operating systems.

### CI / Quality
- Cleared the Ruff format gate (`ruff format` across 34 files) and the Mypy (monorepo) gate by enabling the `pydantic.mypy` plugin for aliased-field call-args.
- Cleared lint, KICS (Checkmarx IaC), Snyk Code, and Docker hardening gates.

### Docs
- README embeds real product screenshots (landing page + analysis output) under `docs/screenshots/` in place of the previous placeholders.
- Refreshed the maintainer release assessment for the 7.6.x line (`docs/internal/reports/`).

### Repository hygiene
- Package version aligned to `7.6.1` across `pyproject.toml`, `apps/web/package.json`, and the web lockfile.

---

## [7.6.0] — 2026-05-28

### Summary
End-user validation hardening release: CLI now fails gracefully on missing output directories and refuses contradictory analyze flags, the Windows console renders accents/em-dashes/emojis correctly, the API caps echoed input in `422` responses, the diagram component stabilizes React Flow renders, and `otm import repo` can emit a chainable `.otm.yaml` seed. No public contract change beyond the new optional `--draft-out` flag and the additional 422 truncation; existing pipelines keep working.

### Highlights
- **CLI** `otm import repo` ganhou `--draft-out <path.otm.yaml>` que materializa um *seed* canónico mínimo (componentes, fronteira, fluxos e ativos) directamente encadeável em `otm validate` / `otm analyze`.
- **CLI** força `UTF-8` em `stdout` / `stderr` no entrypoint e desactiva `legacy_windows` no Rich console: em PowerShell 7, Windows Terminal e VS Code, acentos `pt-BR`, em-dashes `—`, bullets `·`, setas `→` e emojis aparecem íntegros sem `chcp 65001`.
- **API** `RequestValidationError` agora trunca strings/listas/dicts grandes no campo `errors[].input` (cap em 256 chars) — uma `422` para um `title` de 200 KB cabe em <1 KB.
- **UI** `ThreatModelDiagram` move `nodeTypes`/`edgeTypes` para escopo de módulo com `Object.freeze` e centraliza o `markerEnd` de edges, silenciando o aviso "new nodeTypes object" do React Flow em StrictMode.

### Fixed
- `otm init` deixou de vazar `FileNotFoundError` quando o diretório pai não existe: a CLI agora devolve `Failure: cannot write to ...` + `Next step: create the directory first` (`apps/cli/otm_cli/application/init_service.py`).
- `otm analyze --json-out`, `otm precheck --json-out`, `otm diff-analysis --json-out`, `otm report -o`, `otm diagram -o`, `otm export -o`, `otm backlog -o`, `otm import openapi/terraform/k8s/repo --output/--json-out/--explain-out/--draft-out`, e `otm diff --json-out` deixaram de vazar tracebacks quando o diretório de saída não existe; todos passam pelo helper único `shared/emit.write_text_file` + `write_json_file` que valida o `parent` e levanta `CliUserError` legível.
- `otm analyze -m <metodologia> --auto-methodology` deixou de aceitar silenciosamente o conflito; agora dispara `BadParameter` ("mutually exclusive; pass only one") em vez de executar `stride` ignorando o pedido de recomendação automática.

### Changed
- `apps/cli/otm_cli/main.py` configura `PYTHONIOENCODING=utf-8` e chama `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` antes de importar `otm_cli.cli`.
- `apps/cli/otm_cli/commands/bootstrap.py` instancia o Rich `Console(..., legacy_windows=False)` para preservar caixas/painéis íntegros no Windows moderno.
- `apps/web/src/components/diagram/ThreatModelDiagram.tsx`: `EDGE_MARKER_END` ao módulo, `nodeTypes` e `edgeTypes` `Object.freeze` no escopo do ficheiro, e a `<ReactFlow>` recebe ambos.

### Security
- 422 da API deixa de ecoar input completo: o handler em `apps/api/otm_api/errors.py` trunca strings com mais de 256 caracteres com sufixo `…[N chars suppressed]`, listas longas com `…[N items suppressed]` e limita aninhamento, reduzindo amplificação por *input echo* em cenários hostis.
- `SECURITY.md` ganhou uma secção *Postura de implantação* explicando que a API e a UI são desenhadas para uso local; quando expostas, é necessário activar `slowapi`, `OptionalApiKeyMiddleware` e restringir `CORS`.

### Docs
- `docs/README.md` actualiza a referência de versão para `7.6.0` (resolvia drift contra `pyproject.toml`).
- `docs/features/CLI.md` documenta a nova mensagem de erro para `-o`/`--json-out` em directório inexistente, a exclusividade `--methodology` vs `--auto-methodology`, e a postura UTF-8 no Windows.
- `docs/features/ARTIFACT_IMPORT.md` clarifica o âmbito de `otm import repo` ("scan pragmático") e documenta `--draft-out` como caminho oficial para encadear em `validate`/`analyze`.

### Repository hygiene
- `.gitignore` passa a ignorar `_tortura_sandbox/`, `.playwright-mcp/` e `ui-*.png` (artefactos locais da validação extrema).

### Tests
- Nova suite `tests/test_cli_write_paths_and_flag_conflicts.py` cobre os caminhos que antes vazavam traceback e a exclusividade `-m` ↔ `--auto-methodology`.
- Nova suite `tests/test_api_errors_truncate.py` valida o cap de 256 chars em strings/dicts/listas e a preservação dos demais campos do `errors[]`.
- Nova suite `tests/test_cli_import_draft.py` cobre `scan_payload_to_draft_yaml` (estrutura, ativo de sessão, marcação de `/admin`, ausência de inferências) e o encadeamento `import repo --draft-out` → `validate`.
- Suite total: **951 passed, 1 skipped** + **17 testes regressivos novos**.

---

## [7.5.0] — 2026-04-09

### Summary
Release metadata alignment, clearer public changelog narrative, and **Typer/Click** constraints so the CLI and test suite load cleanly on Python 3.12+ (generic `click.Choice` compatibility).

### Highlights
- **Dependencies:** `typer>=0.12.3` and `click>=8.2` for `[cli]` and `[dev]` — avoids `TypeError: type 'Choice' is not subscriptable` when importing the CLI in tests
- More consistent, user-facing **CHANGELOG** wording for the capability set shipped in the 7.4 line
- **SemVer** alignment across `pyproject.toml` and the web app (`7.5.0`) for packaging and GitHub Releases
- Tag **`v.7.5`** follows the repository’s existing `v.7.x` tagging style

### Improvements
- Easier mapping between Git tags and package version for adopters and CI
- Clearer communication of methodology guidance, model validation, and analysis reporting themes

---

## [7.4.0] — 2026-04-07

### Summary
Improved methodology recommendation, stronger model quality validation, and better analysis reporting.

### Highlights
- Refined methodology recommendation and ranking behavior
- Improved model quality precheck for stronger validation
- Added aggregate risk summary to analysis exports
- Better alignment of industry-pack template metadata
- Expanded regression coverage for ranking and catalog consistency

### Improvements
- Better consistency between methodology guidance and engine analysis
- Improved export clarity for decision-making
- Enhanced reliability in catalog and recommendation behavior

---

## [7.3.0] — 2026-04-07

### Summary
Documentation restructuring, improved premium reporting, stronger core validation, and platform governance enhancements.

### Highlights
- Reorganized documentation for better structure and maintainability
- Improved premium reporting (PDF/HTML) with more structured outputs
- Stronger core validation with standardized entity identifiers
- Enhanced Web UI normalization for better comparison and display
- Improved open-source governance (community templates and standards)

### Improvements
- Better consistency across documentation and platform structure
- Improved report quality and readability
- Enhanced CI stability and dependency management

---

## [7.2.0] — 2026-04-02

### Summary
Security and DevSecOps improvements, frontend upgrades, and stronger API controls.

### Highlights
- Optional API security controls (rate limiting and API key support)
- Upgraded frontend stack for better performance and stability
- Strengthened CI/CD with additional security and quality checks
- Improved dependency management for deterministic builds

### Improvements
- Better API behavior and validation handling
- Enhanced test coverage and CI reliability
- Improved frontend stability and build consistency

---

## [7.1.0] — 2026-04-08

### Summary
Internationalization, improved reporting, and stronger platform modularity.

### Highlights
- Full internationalization support (pt-BR / en)
- Localized exports and reporting capabilities
- Improved CLI structure and modularity
- Enhanced API observability and configuration
- Strengthened CI, testing, and security checks

### Improvements
- Better consistency across Web, API, and CLI
- Improved semantic comparison capabilities
- Enhanced documentation structure and clarity

---

## [7.0.0] — 2026-04-07

### Summary
Contract-driven architecture, semantic comparison improvements, and hybrid E2E testing.

### Highlights
- OpenAPI as the single source of truth for contracts
- Improved semantic comparison engine
- Hybrid end-to-end testing across API and UI
- Stronger CI validation for contract consistency

### Improvements
- Better alignment between backend and frontend
- Improved reliability of generated outputs
- Enhanced testing and validation workflows

---

## [6.0.0] — 2026-04-06

### Summary
Stronger type contracts, improved comparison capabilities, and expanded analysis coverage.

### Highlights
- Improved type safety across platform components
- Enhanced semantic comparison with structured insights
- Expanded detection capabilities and analysis coverage
- Improved reporting and export consistency

### Improvements
- Better platform stability and validation
- Increased reliability across workflows
- Enhanced multi-channel output consistency

---

## [5.0.0] — 2026-04-03

### Summary
Improved analysis experience and introduction of advanced modeling capabilities.

### Highlights
- Enhanced analysis UI with decision support features
- Introduction of anti-pattern detection and benchmark metrics
- Improved semantic comparison capabilities
- Repository scanning for artifact import

### Improvements
- Better usability across modeling workflows
- Increased accuracy of analysis results
- Stronger foundation for advanced features

---

## [4.0.0] — 2026-04-02

### Summary
Improved modeling quality and introduction of premium reporting.

### Highlights
- Advanced reporting capabilities
- Improved modeling validation and guidance
- Expanded methodology coverage

### Improvements
- Better consistency across platform components
- Improved output quality and usability

---

## [0.1.0] — 2026-04-01

### Summary
Initial public release introducing the core platform.

### Highlights
- Core threat modeling engine and workflows
- Web UI, API, and CLI integration
- Export capabilities (JSON, Markdown, diagrams)
- Initial methodology support and analysis features
- Basic CI, testing, and validation setup

### Improvements
- Established foundation for future platform growth

---

**License:** MIT
