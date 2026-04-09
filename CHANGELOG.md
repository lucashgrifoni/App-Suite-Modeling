# Changelog

All notable changes to this project are documented here.

This project follows **Keep a Changelog** and **Semantic Versioning**.

---

## [Unreleased]

### Added
- Upcoming improvements and features under development

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
