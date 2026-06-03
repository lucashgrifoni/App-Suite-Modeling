# Changelog

All notable changes to this project are documented here.

This project follows **Keep a Changelog** and **Semantic Versioning**.

---

## [Unreleased]

### Added
- Upcoming improvements and features under development

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
