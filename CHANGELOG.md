# Changelog

Todas as mudanças relevantes neste projeto serão documentadas aqui.

Este arquivo segue o estilo de [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/)
e versionamento semântico quando aplicável.

## [Unreleased]

### Added
- Camada inicial de framework mappings (OWASP TM, OWASP ASVS, NIST CSF, ISO 27001).
- Exportadores iniciais para JSON, Markdown e Mermaid.
- API FastAPI inicial (`/v1/models`, `/v1/templates`, `/v1/exports`).
- UI web inicial com fluxo guiado (criar, revisar, analisar, exportar).
- Branding oficial **App Suite Modeling** com guia de identidade visual.
- PASTA fase 2 incremental (heurísticas risk-centric + insights estruturados).
- PLOT4ai fase 2 incremental (subdomínios AI/LLM + recomendações específicas).
- Smoke suite de release candidate (`tests/test_smoke_release_candidate.py`).
- Documentação de release: checklist, smoke validation, choose methodology e release notes RC1.
- Scripts UI portáteis para CI/Windows: `ci:build:portable`.

### Changed
- Documentação principal alinhada ao estado real do MVP.
- `otm --version` agora mostra a versão instalada do pacote.
- Mensagens de erro da CLI padronizadas com falha, causa e próximo passo.
- CI endurecido com matriz web Linux/Windows e caminho de build portátil no Windows.
- `analysis_markdown` com resumo mais acionável, priorização de riscos e próximos passos.

