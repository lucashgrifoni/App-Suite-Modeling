# Auditoria completa — Clean Code, Clean Architecture e qualidade de engenharia

> **Registo datado — não é o estado corrente do projeto.** Este documento descreve a
> versão que existia quando foi escrito; parte do que afirma já foi corrigido. Ver
> [`docs/internal/README.md`](../README.md) antes de citar qualquer conclusão daqui.


**Projeto:** App Suite Modeling / Open Threat Model  
**Escopo:** monorepo Python (packages, `apps/api`, `apps/cli`) + SPA React/Vite (`apps/web`) + site estático (`gitpage`) + testes, CI, documentação.  
**Metodologia:** revisão estática do código e da estrutura, cruzamento com práticas de Clean Code, Clean Architecture, AppSec/DevSecOps e estratégia de testes. **Nenhuma alteração de código** foi feita nesta fase — apenas diagnóstico.

> **Nota (higiene docs 2026-04):** relatórios de auditoria paralelos com tom “brutal / Staff bar” foram **fundidos** no presente documento e no scorecard/plano de remediação (`FULL_PROJECT_QUALITY_SCORECARD.md`, `FULL_PROJECT_REMEDIATION_*`) para evitar duplicar o mesmo diagnóstico em ficheiros concorrentes.

---

## Resumo executivo

O projeto apresenta **fundação sólida** para um produto de *threat modeling as code*: schema canónico em Pydantic (`otm_core_schema`), motor de análise modular (`otm_threat_engine`), API FastAPI fina que delega regras aos pacotes de domínio, **testes extensivos** (dezenas de ficheiros em `tests/`) e um **gate explícito de fronteira** entre domínio/motor e frameworks (`scripts/check_core_adapter_boundary.py`). A UI usa **tokens CSS + Tailwind** alinhados (`apps/web/tailwind.config.js`), **code-splitting** por rota (`apps/web/src/App.tsx`) e contratos TypeScript alinhados ao backend (testes de alinhamento em `tests/test_*_ts_contract_alignment.py`).

Os principais **gaps de excelência** concentram-se em: (1) **módulo CLI monolítico** (`apps/cli/otm_cli/cli.py`, ~1270 linhas) com alta carga cognitiva e risco de regressão; (2) **postura de segurança assumida como ferramenta local** (API sem autenticação/autorização, CORS fixo para localhost em `apps/api/otm_api/main.py`) — aceitável como *default de desenvolvimento*, mas **não documentado como trust boundary de deployment** de forma uniforme; (3) **CI sem mypy**, sem análise de dependências Node no pipeline Python, e **E2E mínimo no GitHub Actions** (apenas `e2e:smoke:portable` em `.github/workflows/github-ci-cd.yml` + `.github/workflows/security-ci-cd.yml`, enquanto `package.json` define suites mais amplas não obrigatórias no CI); (4) **dependência opcional `sqlalchemy` em `pyproject.toml` [project.optional-dependencies] `api`** sem uso aparente em `apps/api` — ruído de superfície e manutenção; (5) **duas bases front-end** (`apps/web` vs `gitpage`) com risco de **deriva de design system** e esforço duplicado.

**Conclusão operacional:** o projeto está **acima da média** para um OSS de domínio técnico, com **arquitetura em camadas razoável** e **testes fortes no núcleo**, mas **não** cumpre, sem trabalho adicional, o patamar de “excelência técnica” para **exposição genérica na Internet** ou para **equipa grande** sem reduzir dívida no CLI e endurecer gates de CI/segurança.

---

## Nota geral do projeto

**7,0 / 10** — *Bom, com fundação forte e dívidas localizadas de alto impacto.*

---

## Nota por área

| Área | Nota (0–10) | Comentário breve |
|------|-------------|------------------|
| Clean Code | 6,5 | Pacotes núcleo legíveis; CLI “god module”; heurísticas densas no motor. |
| Clean Architecture | 7,5 | Separação packages vs API/CLI; gate de imports; serviços API finos. |
| Frontend / UI | 7,2 | Tokens, lazy routes, componentes; a11y não evidenciada de forma sistemática. |
| Backend / Engine | 7,8 | Validação Pydantic, erros estruturados, motor extensível por heurísticas/packs. |
| Security | 5,8 | Modelo de ameaça assume ferramenta local; uploads limitados; falta hardening “prod”. |
| Testability | 8,0 | Boa pirâmide; smoke release; contratos TS/Python; ainda sem mypy no CI. |
| DevSecOps / Release | 6,3 | Ruff + testes + boundary; falta SCA/SAST alargado, Sonar não integrado no workflow. |
| Maintainability | 7,0 | README e docs ricos; dívidas: CLI gigante, dois fronts, deps órfãs. |

---

## O que está forte

- **Domínio explícito:** `ThreatModelDocument` e análise fora da camada HTTP (`apps/api/otm_api/services/analysis.py` delega a `otm_threat_engine.analyze_document`).
- **Contrato HTTP consistente:** corpos Pydantic, erros com `code`/`message` (`apps/api/otm_api/routers/_errors.py`).
- **Fronteira core ↔ adaptador automatizada:** `scripts/check_core_adapter_boundary.py` impede `fastapi`/`typer` em `otm_core_schema` e `otm_threat_engine`.
- **UI escalável em estrutura:** rotas lazy e layout comum (`apps/web/src/App.tsx`); design tokens via CSS vars mapeados no Tailwind.
- **Testes e smoke de release:** `tests/test_smoke_release_candidate.py` cobre CLI + API + metodologias chave.
- **Segurança de importação de artefactos:** limite de tamanho 2 MiB e validação de negócio nas rotas (`apps/api/otm_api/routers/imports.py`).
- **Consciência de XSS em diagramas:** documentação explícita em `apps/web/src/utils/diagramSanitize.ts` (não usar HTML cru).

---

## O que está médio

- **Motor:** `engine.py` (~275 linhas) orquestra bem, mas acumula políticas (ex.: supressão de ruído STRIDE via `OTM_ENGINE_STRIDE_NOISE_SUPPRESSION`) — *ok mas não ideal* para quem procura políticas plugáveis versionadas.
- **Ruff:** regras limitadas a `E,F,I,UP` em `pyproject.toml` — suficiente para higiene básica, fraco para complexidade ciclomática e smells.
- **Frontend:** `WizardPage.tsx` (~489 linhas) sugere página com múltiplas responsabilidades; ainda gerível, mas tendência a “god component”.
- **Cliente HTTP:** `apiFetch` permite `path` absoluto `http...` (`apps/web/src/api/client.ts`) — flexível, mas exige disciplina nos call sites para não abrir exceções perigosas.

---

## O que está fraco

- **CLI monolítica:** `apps/cli/otm_cli/cli.py` ~1272 linhas — alto acoplamento, difícil navegação e teste fino sem invocar Typer integralmente.
- **API “aberta” por omissão:** sem authz; CORS apenas `localhost:5173` — correto para dev, **insuficiente** para multi-tenant ou exposição pública sem camada extra (API gateway, mTLS, etc.).
- **CI vs qualidade declarada:** `mypy` em `[project.optional-dependencies] dev` mas **ausente** do job `python` em `.github/workflows/github-ci-cd.yml` + `.github/workflows/security-ci-cd.yml`.
- **Sonar:** `sonar-project.properties` existe, mas **não há job** Sonar no workflow CI analisado — config “órfã” operacionalmente.
- **E2E:** CI corre só `e2e/smoke.spec.ts`; `e2e:critical` / `e2e:phase4` existem em `apps/web/package.json` mas não bloqueiam merge — risco de regressão UI.

---

## Principais riscos arquiteturais

1. **Erosão do núcleo:** qualquer import futuro de FastAPI/Typer no motor quebre o gate — bom — mas **lógica de produto** ainda pode migrar para `otm_api` por conveniência e engrossar a camada HTTP.
2. **Duplicação de produto UI:** `gitpage/` vs `apps/web/` — divergência de tokens, acessibilidade e segurança de conteúdo.
3. **Extensão do motor apenas por ficheiros grandes:** `anti_pattern_library` e catálogos YAML — sem fronteira formal de “plugins” pode levar a PRs conflituosas.

---

## Principais riscos de engenharia

- Regressões no **CLI** por superfície única gigante.
- **Contratos** JSON grandes (analyze/export) — mitigado por testes, mas sensível a mudanças de versão do motor.
- **Flakiness potencial E2E** se a suite crítica não correr em CI.

---

## Principais riscos de segurança

- **API sem autenticação:** qualquer cliente na rede que alcance o serviço pode submeter documentos e pedir análise — aceitável só com **trust boundary** explícita (localhost/VPN).
- **CORS permissivo dentro do allowlist dev** (`allow_methods=["*"]`, `allow_headers=["*"]`) — reduz atrito em dev; em staging/prod precisa **restringir**.
- **Armazenamento em `sessionStorage`** do modelo e análise (`apps/web/src/context/SessionContext.tsx`) — qualquer XSS na origem expõe dados do modelo; mitigação depende de CSP rigorosa e sanitização (há atenção em `diagramSanitize.ts`, mas **CSP não foi auditada** neste relatório como implementada no build).

---

## Principais riscos de manutenção futura

- Onboarding em `cli.py`.
- Evolução paralela de **tipos TS** e **modelos Pydantic** — já há testes de alinhamento; ainda assim ponto de atrito.
- **Dependências opcionais não usadas** (`sqlalchemy`) geram perguntas recorrentes em review.

---

## Lista de achados detalhados

Cada achado inclui: **ID**, **categoria**, **severidade** (Crítica / Alta / Média / Baixa), **impacto**, **evidência**.

| ID | Categoria | Severidade | Descrição | Evidência |
|----|-----------|------------|-----------|-----------|
| A-01 | Arquitetura / Clean Code | Alta | CLI como “god module” (~1272 linhas) concentra dezenas de comandos; eleva custo de mudança e teste. | `apps/cli/otm_cli/cli.py` |
| A-02 | Arquitetura | Média | Duas aplicações front-end (`apps/web`, `gitpage`) aumentam custo de design system e revisão de segurança. | Pastas na raiz do repo |
| A-03 | Clean Architecture | Baixa | Motor bem fatiado (`engine.py`, `engine_stride_builder`, etc.), mas políticas de ruído e env vars misturam *policy* com *orquestração*. | `packages/threat-engine/otm_threat_engine/engine.py` |
| A-04 | API / Segurança | Alta (em deployment público) | API sem auth; modelo de ameaça deve assumir rede confiável ou reverse proxy com auth. | `apps/api/otm_api/main.py`, routers |
| A-05 | Segurança | Média | CORS e headers pensados para dev local; não há evidência no mesmo ficheiro de configuração por ambiente. | `apps/api/otm_api/main.py` |
| A-06 | Segurança | Baixa | Uploads limitados a 2 MiB — boa prática MVP; validação de conteúdo depende dos parsers downstream. | `apps/api/otm_api/routers/imports.py` |
| A-07 | Frontend / Segurança | Média | Estado sensível ao modelo em `sessionStorage`; depende de não haver XSS e de origem confiável. | `apps/web/src/context/SessionContext.tsx` |
| A-08 | Frontend / Clean Code | Média | `WizardPage` volumoso — candidato a divisão por passo/feature. | `apps/web/src/pages/WizardPage.tsx` |
| A-09 | Frontend | Baixa | `apiFetch` aceita URL absoluta — útil para testes, risco se usado incorretamente. | `apps/web/src/api/client.ts` |
| A-10 | DevSecOps | Alta | `mypy` não corre no CI — tipo estático declarado mas não enforced. | `pyproject.toml`, `.github/workflows/github-ci-cd.yml` + `.github/workflows/security-ci-cd.yml` |
| A-11 | DevSecOps | Média | Sonar configurado em ficheiro mas não integrado no pipeline CI visível. | `sonar-project.properties` vs `.github/workflows/github-ci-cd.yml` + `.github/workflows/security-ci-cd.yml` |
| A-12 | DevSecOps / Testes | Média | E2E além de smoke não é obrigatório no CI. | `apps/web/package.json`, `.github/workflows/github-ci-cd.yml` + `.github/workflows/security-ci-cd.yml` |
| A-13 | Manutenibilidade | Baixa | `sqlalchemy` em extras `api` sem uso em `apps/api` (grep sem ocorrências). | `pyproject.toml`, `apps/api` |
| A-14 | Clean Code / Qualidade | Média | Ruff com conjunto mínimo de regras — menos deteção de complexidade/bugs. | `pyproject.toml` `[tool.ruff.lint] select` |
| A-15 | Testabilidade | Baixa (forte no geral) | Boa cobertura de testes de domínio; risco residual em caminhos CLI pouco fatiados. | `tests/`, `cli.py` |

---

## Evidências por pasta (amostra representativa)

| Pasta / ficheiro | Papel | Observação |
|------------------|-------|------------|
| `packages/core-schema/otm_core_schema/` | Domínio canónico | ~546 linhas em `document.py` — núcleo pesado mas coeso. |
| `packages/threat-engine/otm_threat_engine/` | Motor + heurísticas | Bem modular; catálogos YAML e bibliotecas de anti-padrões são hotspots de manutenção. |
| `apps/api/otm_api/` | Adaptador HTTP | Finos `services/*`, `routers/*` — alinhado a Clean Architecture pragmática. |
| `apps/cli/otm_cli/` | Adaptador CLI | `cli.py` domina a superfície — principal dívida estrutural. |
| `apps/web/src/` | UI | Tokens + lazy loading; páginas grandes em alguns fluxos. |
| `scripts/check_core_adapter_boundary.py` | Gate arquitetural | Excelente prática automatizada. |
| `.github/workflows/github-ci-cd.yml` + `.github/workflows/security-ci-cd.yml` | CI | Sólido para Python+build web; lacunas mypy/SCA/Sonar/E2E alargado. |

---

## Root cause dos problemas (síntese)

1. **Crescimento orgânico do CLI** sem extração para módulos `commands/` ou pacotes por domínio.
2. **Produto posicionado como toolkit local** — decisões de segurança refletem isso, mas **não estão centralizadas** num documento de *threat model do próprio produto*.
3. **Tooling de qualidade** parcialmente adoptado (mypy, Sonar, E2E expandido) **sem enforcement** no pipeline crítico.
4. **Duplicação de front** típica de marketing site + app — falta estratégia de *shared design tokens* ou monorepo package.

---

## Recomendações priorizadas (visão)

1. Fatiar `cli.py` e introduzir testes unitários por comando.
2. Documentar **trust boundaries** (API/UI/armazenamento) e matriz “dev vs staging vs prod”.
3. Adicionar `mypy` (e gradual typing) ao CI; falhar em erros novos.
4. Integrar SCA (pip + npm) e, se desejado, Sonar no CI.
5. Correr `e2e:critical` no CI ou justificar explicitamente o corte de custo.
6. Remover ou justificar `sqlalchemy` nos extras `api`.
7. Consolidar ou isolar `gitpage` com pacote de tokens partilhado.

---

## O que precisa de refactor leve

- Páginas React com >400 linhas → extrair subcomponentes e hooks.
- Pequenos ajustes de política no motor (extrair funções puras de scoring de tokens STRIDE).
- Ampliar regras Ruff (ex.: subset `B`, `SIM`) com rollout incremental.

---

## O que precisa de refactor estrutural

- **`apps/cli/otm_cli/cli.py`** → múltiplos módulos + camada de aplicação CLI separada de Typer.

---

## O que precisa de redesign arquitetural

- **Exposição pública da API** com multi-utilizador → authn/authz, quotas, logging de auditoria, modelo de tenant — fora do estado actual assumido.
- **Dois fronts** → design system partilhado ou fusão de pipelines de build.

---

## Conclusão final objetiva: excelência técnica?

**Não**, no sentido estrito de “pronto para escala enterprise e exposição aberta na Internet sem ressalvas”.  
**Sim**, no sentido de **OSS bem estruturado para o domínio**, com **separação núcleo/adaptador**, **testes fortes** e **documentação acima da média**.

---

## Respostas às perguntas finais

1. **O projeto segue de verdade boas práticas de Clean Code?** **Parcialmente.** O núcleo e a API são claros; o CLI e algumas páginas UI concentram demasiada responsabilidade.

2. **O projeto segue de verdade boas práticas de Clean Architecture?** **Parcialmente.** A direcção de dependências está correta no núcleo e no motor (reforçada por script); os adaptadores são finos, excepto o CLI.

3. **O projeto está consistente com engenharia sénior de alto nível?** **Em domínio, testes e contratos, sim.** **Em operações de segurança para deployment genérico e em modularização do CLI, ainda não.**

4. **Gaps reais que impedem excelência técnica?** CLI monolítico, modelo de segurança implícito, CI sem mypy/SCA/Sonar, E2E limitado, possível deriva entre dois fronts, dependência opcional não usada.

5. **O que corrigir primeiro para elevar a nota?** (1) Fatiar CLI + testes; (2) endurecer CI (mypy + E2E crítico + SCA); (3) documentar e, se necessário, implementar auth/CORS por ambiente para qualquer cenário não-local.

---

*Documento gerado como entregável de auditoria estática; não substitui pentest, DAST ou revisão de ameaças específica do seu ambiente de deployment.*
