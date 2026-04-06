# Backlog brutal — priorizado por risco e vergonha de engenharia

Prioridade: **P0** (bloqueia credibilidade Staff) · **P1** · **P2** · **P3**

| ID | Problema | Categoria | Severidade | Impacto | Esforço | Prioridade | Arquivos / evidência | Ação recomendada |
|----|----------|-----------|------------|---------|---------|------------|----------------------|------------------|
| B-01 | CLI monolítica (~1272 linhas) | Architecture + Code | ALTO | Alto | L | P0 | `apps/cli/otm_cli/cli.py` | Partir em `otm_cli/commands/*`, camada `application/`, testes por comando; `cli.py` só registo Typer. |
| B-02 | API sem observabilidade | DevOps + Architecture | ALTO | Alto | M | P0 | `apps/api/` (sem logging grepável) | Middleware request-id, logging JSON (nível INFO/WARN/ERROR), duração por rota; opcional OpenTelemetry. |
| B-03 | API sem authn/authz | Security | CRÍTICO* | Alto | L–XL | P0/P1* | `apps/api/otm_api/main.py`, routers | *Se público:* API keys/OAuth + RBAC mínimo. *Se só local:* documento normativo + Docker `internal` + falha CI se `OTM_ENV=prod` sem secrets. |
| B-04 | CORS + métodos/headers `*` | Security | ALTO* | Alto | S | P1 | `apps/api/otm_api/main.py` | `allow_origins`/`methods`/`headers` por env; defaults restritivos fora de `dev`. |
| B-05 | mypy fora do CI | DevOps + Test | ALTO | Médio | S | P0 | `pyproject.toml`, `.github/workflows/ci.yml` | Job `mypy` com strict gradual; falhar em erros novos. |
| B-06 | Sem SCA obrigatório | DevOps + Security | ALTO | Alto | S | P1 | `.github/workflows/ci.yml` | `pip-audit` / advisory; `npm audit`; Dependabot. |
| B-07 | Sonar órfão | DevOps | MÉDIO | Médio | S–M | P2 | `sonar-project.properties` vs `.github/workflows/ci.yml` | Integrar SonarCloud ou remover ficheiro (honestidade). |
| B-08 | E2E smoke só no CI | Test + DevOps | ALTO | Alto | M | P1 | `.github/workflows/ci.yml`, `apps/web/package.json` | `e2e:critical` no PR ou em `main` com bloqueio de release. |
| B-09 | sessionStorage com documento/análise | Security + UI | MÉDIO | Médio | M | P2 | `apps/web/src/context/SessionContext.tsx` | CSP estrita no deploy; revisão XSS; considerar não persistir análise completa. |
| B-10 | Dois fronts (web + gitpage) | Architecture + UI | MÉDIO | Médio | L | P2 | `apps/web/`, `gitpage/` | Pacote partilhado de tokens/componentes ou boundary documentado “não duplicar”. |
| B-11 | Ruff minimal | Code + DevOps | MÉDIO | Médio | S | P2 | `pyproject.toml` | Expandir `select` (B, SIM, …) com correção faseada. |
| B-12 | `except Exception` genérico | Code + Security | BAIXO | Baixo | XS | P3 | `packages/artifact-import/otm_artifact_import/repo_ast_optional.py:48` | Estreitar exceções; log/warn com contexto. |
| B-13 | Hotspots de manutenção (exporters/report) | Code | MÉDIO | Médio | M | P2 | `packages/exporters/otm_exporters/analysis_markdown.py`, `packages/report-premium/otm_report_premium/builder.py` | Extrair secções, testes de caracterização, reduzir ramos por formato. |
| B-14 | Catálogo gigante gerado | Maintainability | MÉDIO | Médio | S | P2 | `packages/industry-packs/otm_industry_packs/catalog/registry_data.py` | Gerar em CI, checksum, ou split por domínio com imports lazy. |
| B-15 | sqlalchemy em extras API sem uso | Architecture | BAIXO | Baixo | XS | P3 | `pyproject.toml`, `apps/api` | Remover ou implementar persistência real com migrações. |

\* **CRÍTICO** para API exposta na Internet; **ALTO** para CORS se o deployment não for estritamente local.

---

## Ordem de execução sugerida (mínimo para subir nota)

1. **B-01 + B-05** (estrutura + tipos)  
2. **B-02 + B-04** (operar + endurecer HTTP por ambiente)  
3. **B-03** conforme modelo de deployment  
4. **B-06 + B-08** (cadeia + UI)  
5. Resto
