# Backlog priorizado de correções e melhorias

Prioridade: **P0** (imediato) · **P1** (curto prazo) · **P2** (médio) · **P3** (longo / opcional).

| ID | Categoria | Título do problema | Descrição | Impacto | Risco | Severidade | Esforço estimado | Prioridade | Arquivos afetados | Recomendação objetiva |
|----|-----------|-------------------|-----------|---------|-------|------------|------------------|------------|-------------------|------------------------|
| BL-01 | Arquitetura / Clean Code | CLI monolítica | ~1272 linhas num único módulo concentram comandos, imports e orquestração. | Alto | Alto regressão | Alta | L (2–5 d) | P0 | `apps/cli/otm_cli/cli.py` | Extrair comandos para `otm_cli/commands/*.py` + camada `application/`; manter `cli.py` só como registo Typer. |
| BL-02 | DevSecOps / Testabilidade | mypy ausente no CI | Tipagem estática não é gate de merge. | Médio | Médio bugs silenciosos | Alta | S (0,5–1 d) | P0 | `pyproject.toml`, `.github/workflows/ci.yml` | Adicionar job `mypy` com config gradual (`strict` por pacote) e lista de exclusões inicial. |
| BL-03 | DevSecOps | SCA não automatizado | Dependências Python/Node sem verificação obrigatória no pipeline. | Médio | Médio supply chain | Alta | S (0,5 d) | P1 | `.github/workflows/ci.yml`, `apps/web/package.json` | `pip-audit` ou `uv pip` + advisory; `npm audit --production` ou OSV; Dependabot. |
| BL-04 | Testes / DevSecOps | E2E mínimo no CI | Apenas smoke; jornadas críticas opcionais. | Médio | Médio regressão UI | Média | M (1–2 d) | P1 | `.github/workflows/ci.yml`, `apps/web/package.json`, `apps/web/e2e/*` | Incluir `npm run e2e:critical` no workflow (com API mock ou stack docker-compose leve). |
| BL-05 | Segurança | API sem auth | Qualquer cliente na rede pode usar endpoints. | Alto (se exposto) | Crítico em público | Alta* | L–XL | P1 | `apps/api/otm_api/main.py`, novos módulos | Documentar “local only”; para público: API key/OAuth + rate limit atrás de gateway. |
| BL-06 | Segurança | CORS e headers de dev | `allow_methods/*`, `allow_headers/*`, origins fixas localhost. | Médio (fora de dev) | Médio | Média | S | P1 | `apps/api/otm_api/main.py` | Parametrizar por env (`OTM_CORS_ORIGINS`); restringir métodos/headers em prod. |
| BL-07 | Manutenibilidade | sqlalchemy extra não usada | Confusão sobre stack de persistência. | Baixo | Baixo | Baixa | XS | P2 | `pyproject.toml` | Remover de `[project.optional-dependencies] api` ou implementar uso real com migrações. |
| BL-08 | DevSecOps | Sonar só em ficheiro | Config existe sem job CI. | Médio | Médio drift qualidade | Média | S–M | P2 | `sonar-project.properties`, `.github/workflows/ci.yml` | Job SonarCloud ou self-hosted; quality gate em PR. |
| BL-09 | Frontend / Clean Code | WizardPage grande | Múltiplas responsabilidades numa página. | Médio | Médio | Média | M | P2 | `apps/web/src/pages/WizardPage.tsx` | Dividir em steps + hooks (`useWizardStep`) + componentes puros. |
| BL-10 | Consistência UI | Dois projetos front | `gitpage` vs `apps/web` podem divergir. | Médio | Médio | Média | L | P2 | `gitpage/`, `apps/web/` | Pacote `packages/ui-tokens` ou submodule de tokens; guia de quando usar cada app. |
| BL-11 | Clean Code | Ruff minimal | Pouca deteção de smells/complexidade. | Médio | Baixo | Baixa | S | P2 | `pyproject.toml` | Expandir `select` com rollout (ex. `B`, `SIM`) e corrigir por fases. |
| BL-12 | Segurança frontend | sessionStorage com modelo | Dados persistidos no browser; risco se XSS. | Médio | Médio | Média | M | P2 | `apps/web/src/context/SessionContext.tsx`, build Vite | Revisar CSP no `index.html`/headers; auditar `dangerouslySetInnerHTML`; considerar `sessionStorage` vs `IndexedDB` encriptado só se requisito. |
| BL-13 | Clean Architecture | Políticas no motor via env | `OTM_ENGINE_STRIDE_NOISE_SUPPRESSION` mistura config ops com código. | Baixo | Baixo | Baixa | S | P3 | `packages/threat-engine/otm_threat_engine/engine.py` | Objecto `EngineConfig` injectável nos testes; env lido num só sítio. |
| BL-14 | API contract | Documentação vs versão API | Garantir que `/v1` e changelogs acompanham evolução do motor. | Médio | Médio | Média | S contínuo | P2 | `docs/API.md`, `CHANGELOG.md` | Checklist de release + testes de contrato por versão. |
| BL-15 | OSS readiness | Badge CI no README | README indica placeholder para badge. | Baixo | Baixo | Baixa | XS | P3 | `README.md` | Substituir por URL real do repo após publicação. |

\*Severidade de segurança **Alta** apenas quando a API é exposta fora de host confiável; em uso local isolado, tratar como **documentação + controlo de rede**.

---

## Ordenação sugerida (primeiras execuções)

1. BL-01 + BL-02 (estrutura + tipos)  
2. BL-03 + BL-04 (cadeia + UI)  
3. BL-05 + BL-06 (se houver deployment não local)  
4. BL-07, BL-08, BL-09, BL-10
