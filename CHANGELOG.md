# Changelog

Todas as mudanças relevantes neste projeto serão documentadas aqui.

Este arquivo segue o estilo de [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e versionamento semântico quando aplicável.

## [Unreleased]

### Added

- Gate decisivo GO/NO-GO de uma página para publicação (`docs/GO_NO_GO_v0.1.0.md`).

### Changed

### Fixed

<!-- Compare links: atualizar com URL do repositório remoto após primeiro push de tag. -->

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
