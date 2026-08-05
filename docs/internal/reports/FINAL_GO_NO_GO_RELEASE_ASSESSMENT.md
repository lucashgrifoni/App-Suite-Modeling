# Avaliação final de lançamento (GO / NO-GO) — App Suite Modeling / open-threat-model

> **Registo datado — não é o estado corrente do projeto.** Este documento descreve a
> versão que existia quando foi escrito; parte do que afirma já foi corrigido. Ver
> [`docs/internal/README.md`](../README.md) antes de citar qualquer conclusão daqui.


> **Reavaliação atual:** `7.6.1` — 2026-06-03 (secção abaixo). A avaliação original `7.2.0` (2026-04-01) é mantida como **histórico** mais adiante.

---

## 2026-06-03 — Reavaliação em `v7.6.1` (corrente)

**Tipo:** Release/launch readiness + OSS publication readiness  
**Versão de pacote:** `7.6.1` (`pyproject.toml`, `apps/web/package.json`, lockfile alinhados)  
**Decisão:** **GO — publicar como OSS público.**

### Evidência verificada nesta rodada

| Critério | Resultado | Fonte |
|----------|-----------|-------|
| Testes | **951 passed / 1 skipped** | CHANGELOG 7.6.0 + runs CI |
| Cobertura / qualidade | **100%**, SonarQube Quality Gate **OK**, 0 issues/bugs/vulns/hotspots | STATUS sessão 2026-05-27 |
| CI funcional (GitHub CI/CD) | **Verde** no HEAD (`a3de5a0`) | `gh run view` |
| CI de segurança (Security CI/CD) | **Verde** no push de 2026-05-28; vermelho apenas em runs *scheduled*/*PR* | `gh run view` |
| Causa do vermelho | **GHAS code scanning desligado em repo privado** (CodeQL + upload SARIF exigem-no) — não há *findings* reais | logs do run scheduled 26744057797 |
| Segredos no histórico | **gitleaks: no leaks found** (110 commits, 5.32 MB) | scan local |
| Vazamento de e-mail/caminho local | Nenhum em ficheiros rastreados (só username/URL pública do GitHub) | grep tracked |
| Dependabot | **0 alertas abertos** | `gh api dependabot/alerts` |
| OSS hygiene | LICENSE MIT, SECURITY, CONTRIBUTING, CODE_OF_CONDUCT, templates issue/PR, CODEOWNERS | repo |
| Screenshots no README | **Embebidos** (landing + análise) sob `docs/screenshots/` | README |

### Porque é GO

O único gate vermelho (Security CI/CD em *scheduled*/*PR*) **resolve-se ao tornar o repositório público**: em repos públicos, CodeQL, upload de SARIF e *dependency review* são gratuitos. Como a publicação é o objetivo declarado, o ato de publicar fecha o gate em vez de o contornar. Não há *findings* de segurança reais a bloquear, nem segredos no histórico, nem claims enganosas no README (tabela de maturidade honesta: sem persistência server-side por defeito, perímetro de API opcional, import como rascunho).

### Condições / pós-publicação (não bloqueantes)

1. **Visibilidade pública** reativa code scanning/CodeQL/dependency-review (grátis) — re-correr Security CI/CD e confirmar verde.
2. **Branch protection** em `main` (estava deixada de fora por ser repo solo privado).
3. **Deprecação Node 20 → Node 24** em algumas actions (apenas *warning* atual; acompanhar antes de set/2026).
4. Tag **`v7.6.1`** publicada + GitHub Release a partir do CHANGELOG.

### Risco residual

- Análise é **heurística/assistiva**, não prova de completude (já explícito no README/KNOWN_LIMITATIONS).
- API/UI desenhadas para uso local; exposição à internet exige `slowapi`, API key opcional e CORS restrito (documentado em SECURITY.md e DEPLOYMENT_INVARIANTS).

---

## 2026-04-01 — Avaliação original em `v7.2.0` (histórico)

**Data:** 2026-04-01  
**Tipo:** Auditoria de *release readiness* / *launch readiness* (open source)  
**Versão de pacote referida:** `7.2.0` (`pyproject.toml`, `apps/web/package.json`)

---

## Executive summary

O repositório apresenta **produto coerente** (threat modeling as code, documento canónico, CLI + API + UI), **engenharia credível** (CI extensa, 400+ testes Python, gates de contrato OpenAPI, documentação rica) e **onboarding objetivo** no README. Os principais **gaps para um lançamento “premium”** são **percepção visual** (screenshots ainda não embutidas no README), **narrativa de versionamento** (histórico `v0.1.0` vs linha `7.x` — agora clarificada em `docs/VERSIONING_AND_TAGS.md`) e **OSS hygiene** que faltava parcialmente (**Código de conduta**, **templates de issue/PR**), já **corrigidos nesta rodada**.

Não foram identificados **blockers éticos ou técnicos** que imponham **NO-GO** para publicação como OSS **desde que** as expectativas de maturidade (sem persistência server-side por defeito, perímetro API opcional, import como rascunho) fiquem visíveis — o que o README e `KNOWN_LIMITATIONS.md` agora reforçam de forma alinhada.

---

## Decisão final: **GO WITH CAVEATS**

### Justificativa objectiva

| Critério “GO” estrito | Avaliação |
|------------------------|-----------|
| Coerência produto ↔ código | **Sim** — monorepo, um schema, mesmos fluxos CLI/API. |
| README forte para visitante frio | **Quase** — melhorado; ainda **sem** imagens reais no topo. |
| Quick start verificável | **Sim** — `pip install -e ".[dev,cli,api]"`, `otm validate/analyze/report` sobre `examples/minimal.otm.yaml`. |
| Documentação central consistente | **Sim** — índice em `docs/README.md`, limitações honestas, deployment invariants. |
| OSS mínimo crédivel | **Sim** (após esta rodada) — LICENSE MIT, CONTRIBUTING, SECURITY, Código de conduta, templates. |
| Risco reputacional claro ao publicar | **Mitigado** — maturidade e limitações explicitadas; sem claims de “SaaS completo” no README. |

**Caveats** (não bloqueiam GO, mas devem figurar na comunicação de release):

1. **Visual:** README ainda Lista *placeholders* para screenshots; impacto na primeira impressão em redes sociais / Hacker News.  
2. **Versão Git vs. histórico:** equipas devem etiquetar releases (ex. `v7.2.0`) alinhadas ao `pyproject.toml` (secção nova em versionamento).  
3. **Ambiente local:** contribuidores precisam de extras corretos (`[api]` para testes que importam `slowapi`); documentado no README.

**NO-GO** seria forçado por: testes principais a falhar no CI, documentação enganosa sobre auth/persistência, ou ausência de LICENSE/SECURITY — **não é o caso**.

---

## Estado actual do repositório (snapshot)

- **Python:** pacote instalável `open-threat-model`, namespaces `otm_*`, extras `api`, `cli`, `dev`, `report`, `artifact_import_ast`.  
- **Apps:** FastAPI (`otm_api`), Typer (`otm`), React/Vite 8 (`apps/web`).  
- **CI:** `.github/workflows/github-ci-cd.yml` + `.github/workflows/security-ci-cd.yml` — Ruff, Bandit, mypy multi-pacote, pip-audit, pytest, smoke RC, Semgrep, Trivy imagem API, build web (Ubuntu + Windows), npm audit, E2E smoke/critical/hybrid.  
- **Documentação:** dezenas de guias; índice em `docs/README.md`; profundidade em `PROJECT_DEEP_DIVE.md`, layout em `REPOSITORY_LAYOUT.md`.  
- **Segurança OSS:** `SECURITY.md` com canal privado; política Semgrep; cabeçalhos/CSP documentados para web.

---

## Avaliação por eixo

### A. Produto e posicionamento

**Fortes:** Proposta de valor clara para AppSec / DevSecOps / arquitectos; diferencial (canónico + multi-metodologia + PLOT4ai + import + diff) explícito; escopo realista (MVP maduro, não produto multitenant completo).  
**Riscos:** Visitantes podem esperar “contas e histórico na cloud” — mitigado por tabela de maturidade no README e `KNOWN_LIMITATIONS.md`.

### B. README (raiz)

**Fortes:** Acima da dobra: o quê, para quem, problema, fluxo, *quick start*, exemplos CLI, tabela API, limitações, contribuição.  
**Melhorias aplicadas:** nota `open-threat-model` vs marca; pré-requisitos Node **20**; tabela **Maturity**; secção screenshots mais honesta; CONTRIBUTING/CODE_OF_CONDUCT/CHANGELOG/versioning ligados.  
**Residual:** inclusão futura de ficheiros PNG sob `docs/screenshots/`.

### C. Quick start / onboarding

**Fortes:** `setup_dev.py` / `run_dev.py`, caminhos Windows/Linux no `docs/README.md`.  
**Melhorias:** Explicação de extras `dev,cli,api` vs instalação mínima; artefacto de saída (`REPORT.md`) descrito; Cairo/Linux mencionado para quem instala `[dev]` completo.  
**Residual:** Novos utilizadores em Windows com caminhos exóticos devem usar `ci:build:portable` (já em limitações).

### D. Documentação (arquitectura)

**Fortes:** MONOREPO, REPOSITORY_LAYOUT, PROJECT_DEEP_DIVE, KNOWN_LIMITATIONS, API, CLI, I18N.  
**Melhorias:** VERSIONING clarifica `7.x` vs `v0.1.0` histórico; API client compatibility em limitações sem referência obsoleta a `0.x` apenas.  
**Residual:** Volume alto de docs — o índice em `docs/README.md` é essencial (não escondido).

### E. OSS / comunidade

**Antes:** Faltavam Código de conduta e templates GitHub formais.  
**Depois:** `CODE_OF_CONDUCT.md` (Contributor Covenant 2.1 PT); `.github/ISSUE_TEMPLATE/*`; `.github/pull_request_template.md`; CONTRIBUTING referencia CoC.  
**Residual:** `SECURITY.md` referencia “canal privado definido” — após publicar, garantir que *Security Advisories* do repositório estão activos.

### F. Confiabilidade e execução

**Validação:** Com `pip install -e ".[dev,cli,api]"`, `pytest` reportou **411 passed, 1 skipped** na máquina de auditoria. README alinha com necessidade do extra `[api]` para testes que carregam a API.  
**Impressão:** Comandos do *quick start* foram executados (`otm analyze … --methodology stride`) com sucesso.

### G. Higiene final

**Acções:** Pequenas correcções de consistência; sem remoção em massa de Markdown; sem refactor de pastas.  
**Ligações:** `tests/test_docs_links.py` deve permanecer verde após adição de links relativos nos novos `.md`.

---

## Principais melhorias executadas nesta rodada

- README: maturidade, packaging, pré-requisitos, screenshots honestos, ligações OSS.  
- `docs/VERSIONING_AND_TAGS.md`: secção de alinhamento `pyproject` / tags / marco `v0.1.0`.  
- `docs/KNOWN_LIMITATIONS.md`: linguagem de compatibilidade API actualizada.  
- `CODE_OF_CONDUCT.md` + templates GitHub + PR template.  
- `CONTRIBUTING.md`: referência ao Código de conduta.  
- `docs/README.md`: entradas para este pacote de avaliação de lançamento.  
- Três documentos de auditoria: este ficheiro, scorecard, log de execução.

---

## Pendências remanescentes (não bloqueantes)

| Item | Severidade | Impacto no lançamento | Bloqueia? |
|------|------------|------------------------|-----------|
| Screenshots no README | Média | *Trust* visual / partilha social | Não |
| Badge CI com URL real | Baixa | Sinal de saúde em tempo real | Não |
| Tag Git `v7.2.0` (ou próxima) publicada | Média | Reprodutibilidade para utilizadores | Não para “abrir o repo” |
| Traduzir README para PT (opcional) | Baixa | Audiências lusófonas | Não |

---

## Riscos residuais

- **Expectativas de “produto cloud”** se a comunicação de release omitir limitações — mitigação: destacar tabela de maturidade.  
- **Manutenção de dependências Node/Python** — já mitigado por Dependabot e gates npm/pip-audit no CI; risco operacional normal de OSS.

---

## Recomendação final

**Publicar como open source** com comunicação explícita: *ferramenta sólida para equipas técnicas*, **não** substituto completo de IdP/OIDC/persistência multitenant sem trabalho de envolvimento. Próximo passo operacional sugerido: **capturar 3–5 screenshots** conforme `SCREENSHOT_GUIDE.md`, abrir release GitHub com notas a partir de `CHANGELOG.md`, e adicionar badge de CI real.

---

*Documento produzido no âmbito da rodada de release readiness; não substitui parecer legal ou de segurança organizacional do adotante.*
