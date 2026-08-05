# Log de execução — rodada final de release readiness

> **Registo datado — não é o estado corrente do projeto.** Este documento descreve a
> versão que existia quando foi escrito; parte do que afirma já foi corrigido. Ver
> [`docs/internal/README.md`](../README.md) antes de citar qualquer conclusão daqui.


**Data:** 2026-04-01  
**Âmbito:** Auditoria GO/NO-GO + melhorias pequenas e seguras (sem refactor estrutural)

---

## 1. O que foi inspeccionado

| Área | Método |
|------|--------|
| README raiz | Leitura integral; avaliação “20 segundos”, quick start, ligações, tono OSS |
| `docs/README.md` | Coerência com README, versão vs `pyproject.toml`, índice |
| `docs/MONOREPO.md`, `REPOSITORY_LAYOUT.md`, `PROJECT_DEEP_DIVE.md` | Amostragem de consistência com estrutura real |
| `docs/VERSIONING_AND_TAGS.md`, `docs/KNOWN_LIMITATIONS.md` | Conflitos narrativos (7.x vs v0.1.0; API 0.x) |
| OSS | `LICENSE`, `CONTRIBUTING.md`, `SECURITY.md`, existência de `CODE_OF_CONDUCT`, `.github/*` templates |
| CI | Leitura de `.github/workflows/github-ci-cd.yml` + `.github/workflows/security-ci-cd.yml` (Python 3.12, Node 20, jobs) |
| `pyproject.toml` / `apps/web/package.json` | Versões e extras |
| Quick start real | Execução `otm analyze examples/minimal.otm.yaml --methodology stride` |
| Testes | `pytest` completo após `pip install -e ".[dev,cli,api]"` |
| Ligações Markdown | `tests/test_docs_links.py` (após alterações) |

---

## 2. O que foi alterado

| Ficheiro | Alteração |
|----------|-----------|
| `README.md` | Nota de packaging; Node 20+; secção **Maturity**; pré-requisitos; clarificação extras pip; outputs de exemplo; screenshots honestos; methodology/branding EN; contributing com CoC/templates/versioning |
| `docs/VERSIONING_AND_TAGS.md` | Secção **Alinhamento pyproject / tags**; exemplos de tags `7.x` |
| `docs/KNOWN_LIMITATIONS.md` | Frase de compatibilidade API sem referência obsoleta exclusiva à série 0.x |
| `docs/README.md` | Secção avaliação lançamento + linhas no índice |
| `CONTRIBUTING.md` | Ligação a `CODE_OF_CONDUCT.md` |
| `CODE_OF_CONDUCT.md` | **Novo** — Contributor Covenant 2.1 (PT) |
| `.github/ISSUE_TEMPLATE/bug_report.yml` | **Novo** |
| `.github/ISSUE_TEMPLATE/feature_request.yml` | **Novo** |
| `.github/ISSUE_TEMPLATE/config.yml` | **Novo** |
| `.github/pull_request_template.md` | **Novo** |
| `docs/internal/reports/FINAL_GO_NO_GO_RELEASE_ASSESSMENT.md` | **Novo** |
| `docs/internal/reports/FINAL_RELEASE_SCORECARD.md` | **Novo** |
| `docs/internal/logs/FINAL_RELEASE_EXECUTION_LOG.md` | **Novo** (este ficheiro) |

---

## 3. O que foi mantido sem alteração

- Estrutura de pastas `packages/` e `apps/`.  
- `pyproject.toml` (`packages.find`, versão `7.2.0`).  
- Pipelines CI existentes.  
- Dockerfiles e contratos OpenAPI (não regenerados nesta rodada).  
- Documentação longa preexistente (auditorias `FULL_*`, guias de produto) — sem limpeza agressiva.

---

## 4. Fora de escopo (explícito)

- Refactor de código de domínio ou UI.  
- Nova funcionalidade de produto.  
- Geração de screenshots reais (sem ambiente gráfico / decisão de branding visual).  
- Publicação efectiva no PyPI/GitHub (operacional do mantenedor).  
- Tradução completa do README para português.

---

## 5. Validações executadas e resultado

| Validação | Comando / acção | Resultado |
|-----------|-------------------|-----------|
| Suite pytest (ambiente com `[api]`) | `pip install -e ".[dev,cli,api]"` · `python -m pytest` | **411 passed, 1 skipped** |
| Smoke CLI | `otm analyze examples/minimal.otm.yaml --methodology stride` | **Exit code 0** |
| Links docs | `python -m pytest tests/test_docs_links.py -q` | **1 passed** (executar após commits finais) |

**Nota:** Num venv **sem** extra `[api]`, a recolha de testes que importam `otm_api` falha em `slowapi` — comportamento esperado; o README agora orienta para `pip install -e ".[dev,cli,api]"` para desenvolvimento completo.

---

## 6. Decisão registada

**GO WITH CAVEATS** — detalhes e justificativa em [`FINAL_GO_NO_GO_RELEASE_ASSESSMENT.md`](../reports/FINAL_GO_NO_GO_RELEASE_ASSESSMENT.md).

---

*Log objetivo para auditoria interna e continuidade entre mantenedores.*
