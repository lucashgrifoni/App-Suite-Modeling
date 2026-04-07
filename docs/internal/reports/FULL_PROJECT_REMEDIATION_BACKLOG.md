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
| BL-08 | DevSecOps | Sonar só em ficheiro | Config existe sem job CI. | Médio | Médio drift qualidade | Média | S–M | P2 | `sonar-project.properties`, `.github/workflows/ci.yml` | SonarQube localhost (manual) ou CI com runner self-hosted; quality gate em PR se aplicável. |
| BL-09 | Frontend / Clean Code | WizardPage grande | Múltiplas responsabilidades numa página. | Médio | Médio | Média | M | P2 | `apps/web/src/pages/WizardPage.tsx` | Dividir em steps + hooks (`useWizardStep`) + componentes puros. |
| BL-10 | Consistência UI | Dois projetos front | `gitpage` vs `apps/web` podem divergir. | Médio | Médio | Média | L | P2 | `gitpage/`, `apps/web/` | Pacote `packages/ui-tokens` ou submodule de tokens; guia de quando usar cada app. |
| BL-11 | Clean Code | Ruff minimal | Pouca deteção de smells/complexidade. | Médio | Baixo | Baixa | S | P2 | `pyproject.toml` | Expandir `select` com rollout (ex. `B`, `SIM`) e corrigir por fases. |
| BL-12 | Segurança frontend | sessionStorage com modelo | Dados persistidos no browser; risco se XSS. | Médio | Médio | Média | M | P2 | `apps/web/src/context/SessionContext.tsx`, build Vite | Revisar CSP no `index.html`/headers; auditar `dangerouslySetInnerHTML`; considerar `sessionStorage` vs `IndexedDB` encriptado só se requisito. |
| BL-13 | Clean Architecture | Políticas no motor via env | `OTM_ENGINE_STRIDE_NOISE_SUPPRESSION` mistura config ops com código. | Baixo | Baixo | Baixa | S | P3 | `packages/threat-engine/otm_threat_engine/engine.py` | Objecto `EngineConfig` injectável nos testes; env lido num só sítio. |
| BL-14 | API contract | Documentação vs versão API | Garantir que `/v1` e changelogs acompanham evolução do motor. | Médio | Médio | Média | S contínuo | P2 | `docs/features/API.md`, `CHANGELOG.md` | Checklist de release + testes de contrato por versão. |
| BL-15 | OSS readiness | Badge CI no README | README indica placeholder para badge. | Baixo | Baixo | Baixa | XS | P3 | `README.md` | Substituir por URL real do repo após publicação. |

\*Severidade de segurança **Alta** apenas quando a API é exposta fora de host confiável; em uso local isolado, tratar como **documentação + controlo de rede**.

---

## Ordenação sugerida (primeiras execuções)

1. BL-01 + BL-02 (estrutura + tipos)  
2. BL-03 + BL-04 (cadeia + UI)  
3. BL-05 + BL-06 (se houver deployment não local)  
4. BL-07, BL-08, BL-09, BL-10

---

## Itens adicionais (consolidação documental — ex-identificadores B-xx)

| ID | Categoria | Título | Prioridade | Notas |
|----|-----------|--------|------------|-------|
| BL-16 | Código | `except` largos em import AST opcional | P3 | `packages/artifact-import/.../repo_ast_optional.py` — estreitar exceções; telemetria de falha. |
| BL-17 | Código / Exporters | Exporters e report premium volumosos | P2 | Secções menores; testes de caracterização. |
| BL-18 | Manutenção | Catálogo `registry_data` extenso | P2 | Split ou geração em CI / checksum. |

---

## Registo de mitigações (ex-backlog paralelo, transparência)

| Tema | Estado | Onde ver |
|------|--------|----------|
| OpenAPI desatualizado sem falhar CI | Mitigado | `scripts/verify_openapi_up_to_date.py`, job CI |
| E2E só contra mock | Parcial | `e2e:hybrid`, API real + Vite |
| Tipos TS vs API | Parcial | `openapi-typescript`, `npm run contracts:sync` |
| API sem observabilidade | Mitigado | `otm_api.observability` — ver [`CI_AND_SECURITY_EVIDENCE.md`](../../CI_AND_SECURITY_EVIDENCE.md) |
| CLI monolítica | Mitigado | `commands/` + `application/` — idem |
| `mypy` fora do CI | Mitigado | Job CI + `pyproject.toml` |
| SCA obrigatório | Mitigado | pip-audit, npm audit, Dependabot |
| CORS “sempre dev” | Mitigado | `OTM_ENV` / `OTM_CORS_ORIGINS` — idem |
