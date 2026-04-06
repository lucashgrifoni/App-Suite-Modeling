# Relatório de auditoria brutal — Principal / Staff / Architect / AppSec

**Escopo:** monorepo completo (Python: `packages/*`, `apps/api`, `apps/cli`; React/Vite: `apps/web`; marketing: `gitpage/`; CI, testes, configs).  
**Postura:** crítica, sem suavização. “Funciona” e “passa CI” **não** equivalem a excelência.  
**Método:** leitura sistémica + amostragem de hotspots + grep estruturado (p.ex. ausência de logging na API, tamanho de módulos, gates de CI).

---

## Resumo executivo

Este repositório é **acima da média para um OSS de domínio técnico**: há modelo canónico sério (Pydantic), motor de análise modular, API fina que delega regras, **script automatizado de fronteira** `scripts/check_core_adapter_boundary.py`, e **muitos testes** em `tests/`. Isso coloca o projeto confortavelmente no patamar **Senior+ em modelagem de domínio e testes de núcleo**.

**Não** atinge o bar que um **Staff ou Principal** aplica a um **produto de plataforma** exposto a escala, multi-equipa e risco operacional/segurança: a CLI é um **monólito** (~1272 linhas em `apps/cli/otm_cli/cli.py`), a **API carece de observabilidade** (sem `logging`/tracing evidente em `apps/api`), **sem autenticação/autorização**, CORS e política HTTP pensados para **dev local** (`apps/api/otm_api/main.py`), **CI sem mypy** apesar de `mypy` nas deps de dev (`pyproject.toml`), **sem SCA obrigatório**, **Sonar só em ficheiro** (`sonar-project.properties`) sem job no workflow, e **E2E mínimo** no GitHub Actions (`.github/workflows/ci.yml` vs scripts mais largos em `apps/web/package.json`).

**Veredicto direto:** o projeto **não** é “10/10 real” nem “nível Staff/Principal” para um sistema **distribuído e operado em produção genérica**. É **Senior forte em núcleo de produto**, com **dívida e risco concentrados** em CLI, operações, segurança perimetral da API e gates de qualidade contínua.

---

## Nota REAL do projeto (0–10)

**6,8 / 10** — nota de **engenharia global honesta** (código + ops + segurança + sustentabilidade).

- Se avaliar **só** o núcleo de domínio e motor: **7,5–8,0**.  
- Se avaliar **plataforma pronta para escala e superfície de ataque real**: **5,0–6,0**.

---

## Comparação com nível esperado

| Nível | Onde o projeto encaixa |
|-------|------------------------|
| Junior | — |
| Mid | Alguns aspetos de scripts e páginas UI isoladas |
| **Senior** | **Domínio, motor, testes de núcleo, contratos Pydantic** |
| Staff | **Não** — faltam padrões de plataforma (observabilidade, threat model de deployment, gates completos) |
| Principal | **Não** — decisões de escala, risco sistémico e custo de mudança ainda não estão domesticados (CLI monolítica, CI incompleto para o discurso de qualidade) |

**Síntese:** entre **Senior** e **Staff**, **mais próximo de Senior** quando o critério é o **todo** (não só o pacote `otm_core_schema`).

---

## Onde o projeto está acima da média (sem papas na língua)

- **Fronteira arquitetural automatizada:** proibir FastAPI/Typer no core/motor é disciplina que muitas empresas **não** têm.
- **API como adaptador:** `apps/api/otm_api/services/analysis.py` delega; routers validam com Pydantic — **direção de dependência correta**.
- **Volume e profundidade de testes** em `tests/` + smoke de release (`tests/test_smoke_release_candidate.py`).
- **Alinhamento contrato TS/Python** (`tests/test_analysis_ts_contract_alignment.py`, `tests/test_comparison_ts_contract_alignment.py`) — sinal de maturidade rara em OSS pequeno.
- **UI:** tokens via CSS vars + Tailwind (`apps/web/tailwind.config.js`), lazy routes (`apps/web/src/App.tsx`), vários padrões **a11y** (ex.: `role="alert"`, `aria-live`, progressbar em componentes) — **não é um front genérico de tutorial**.

---

## Onde está abaixo do esperado (sem suavizar)

- **CLI como “god module”:** um ficheiro ~1272 linhas é **anti-padrão** para equipa >1 e para revisão segura; é **ponto único de conflito** e regressão.
- **API `version="0.1.0"`** com **zero logging** grepável em `apps/api` — em incident response isto é **falha de engenharia de plataforma**, não “detalhe”.
- **Segurança de deployment:** CORS fixo em localhost + `allow_methods=["*"]` + `allow_headers=["*"]` — **adequado a dev**, **inaceitável como política final** para ambiente partilhado sem camada explícita (gateway, mTLS, VPN).
- **CI que não reflete o toolchain declarado:** `mypy` no `[project.optional-dependencies] dev` mas **ausente** do job Python em `.github/workflows/ci.yml` — **hipocrisia de qualidade** (dizes que tipas, não obrigas).
- **E2E:** smoke único no CI; existem `e2e:critical`, `e2e:phase4` em `package.json` que **não bloqueiam** merge — **janela de regressão UI deliberada**.
- **Dados do modelo em `sessionStorage`** (`apps/web/src/context/SessionContext.tsx`) — superfície de **XSS = exfiltração do threat model**; mitigação depende de CSP e higiene de renderização (há consciência em `apps/web/src/utils/diagramSanitize.ts`, mas **CSP/build não foi provada** nesta auditoria como gate).
- **Artefacto de catálogo gigante:** `packages/industry-packs/otm_industry_packs/catalog/registry_data.py` (~1489 linhas) — típico de dados gerados; **reviews humanos degradam** e erros são **sistémicos** se o gerador falhar.

---

## TOP PROBLEMAS (Top 10) — só o que realmente importa

| # | Problema | Porque é grave |
|---|----------|----------------|
| 1 | **CLI monolítica** (`cli.py` ~1272 linhas) | Escala de equipa quebra aqui primeiro: conflitos, medo de mudar, testes difíceis de isolar. |
| 2 | **API sem observabilidade** (sem logging evidente) | Staff/Principal **exige** rastreio de falhas, latência e abuso; hoje é caixa negra operacional. |
| 3 | **API sem authn/authz** | Qualquer processo na rede = cliente; **não é** secure-by-design para multi-inquilino ou Internet. |
| 4 | **Política CORS/HTTP permissiva** no código da app | Erro clássico de copiar “dev” para staging; **superfície CSRF/CORS mal compreendida** quando exposto. |
| 5 | **mypy fora do CI** | Tipos são **documentação executável**; sem gate, divergem da realidade. |
| 6 | **Sem SCA obrigatório** (pip/npm) no pipeline | Supply chain **não** é tratada como risco de 1ª classe. |
| 7 | **Sonar configurado, não integrado** | Config órfã = **ilusão** de quality gate. |
| 8 | **E2E crítico não obrigatório** | Regressão de jornada **não** é preço de merge. |
| 9 | **Estado sensível no browser** (`sessionStorage`) | Modelo de ameaças do **próprio produto** precisa assumir XSS; muitos times subestimam. |
| 10 | **Ruff minimal** (`E,F,I,UP` só) | Pouca deteção de bugs/complexidade; **abaixo** do que “Big Tech” usa como baseline. |

---

## PROBLEMAS SISTÉMICOS

1. **Discurso de qualidade > enforcement:** ferramentas listadas (`mypy`, Sonar, suites E2E) **existem**; parte **não** falha o pipeline — padrão de **risco aceite implicitamente**.
2. **Duplicação de superfície de produto:** `apps/web` + `gitpage/` — **deriva** de tokens, a11y e segurança de conteúdo; custo duplicado **sistémico**.
3. **Dois “adaptadores” desiguais:** API modular vs CLI monolítica — **inconsistência de engenharia** na mesma codebase; novos features tendem a ir para o sítio mais fácil (sou **cético**: já foi para a CLI).
4. **Segurança implícita “ferramenta local”:** aceitável **só** se **documentado como invariante de deployment** e validado em CI/docs; não vi **contrato formal** de threat model do produto no repo (além de `SECURITY.md` para divulgação responsável — isso é **outra coisa**).

---

## ROOT CAUSE ANALYSIS

| Sintoma | Root cause provável |
|---------|---------------------|
| CLI gigante | Crescimento orgânico sem **barreira de modularização** nem owner de “application layer” da CLI. |
| mypy/Sonar/E2E largos fora do CI | **Otimização de tempo de pipeline** e **ausência de política de risco** que diga “isto não é opcional”. |
| API sem logs | Foco em **features de domínio**; **plataforma** (SRE, observabilidade) não foi prioridade — típico de produto ainda “library-first”. |
| CORS permissivo | **DX** sobre **postura zero-trust**; falta **config por ambiente** com valores seguros por defeito em `prod`. |
| registry_data enorme | **Dados como código** sem pipeline de geração/validação visível no mesmo PR — **processo**, não só ficheiro. |

---

## RISCOS

### Curto prazo
- Regressão em **CLI** ou **exportadores** (`packages/exporters/otm_exporters/analysis_markdown.py` ~597 linhas — hotspot) ao mexer em contratos JSON.

### Médio prazo
- **Drift** TS/Python mesmo com testes de alinhamento — cada campo novo é **ponto de atrito** se não houver OpenAPI gerado como fonte de verdade.

### Longo prazo
- **Onboarding** lento; **Staff não escala** o conhecimento preso em ficheiros longos; **forks** ou **stagnação** se o custo de mudança superar valor.

---

## DÍVIDA TÉCNICA REAL

- **Já séria:** `apps/cli/otm_cli/cli.py` (estrutural).  
- **Já séria para ops:** ausência de logging/metrics na API.  
- **Acumulada:** CI que não espelha o toolchain de tipos e qualidade estática completa.  
- **Quick fix disfarçado:** CORS `*` em métodos/headers — “funciona no meu laptop”.

---

## NECESSIDADE DE REFACTOR

### Leve
- Expandir regras Ruff com rollout incremental.  
- Extrair funções puras de políticas no motor (`engine.py` — supressão STRIDE via env).

### Estrutural
- **Partir `cli.py`** em módulos de comando + camada de aplicação + testes por comando.

### Arquitetural
- **Exposição pública da API:** auth, rate limit, observabilidade, configuração por ambiente — ou **posicionamento explícito** “library + exemplo Docker rede interna apenas”.

---

## Conclusão brutal

O projeto **não** atinge nível **Staff/Principal** no **todo**. Atinge **Senior+** em **partes** (domínio, motor, testes). A **ilusão de excelência** vem de código núcleo sólido **acoplada** a **lacunas de plataforma e de modularização do adaptador CLI**.

**Porque não é 10/10:** 10/10 exigiria **gates alinhados ao discurso**, **observabilidade**, **superfície de ataque tratada por design** (ou explicitamente recusada com enforcements de deployment), e **ausência de god modules** em adaptadores críticos.

---

## Critérios finais (respostas diretas)

1. **Nível Staff/Principal de verdade?** **Não** (globalmente). **Sim** em fragmentos (domínio/testes).  
2. **Pronto para escala real?** **Não** sem camada de plataforma (auth, limites, logs, métricas, política de dados).  
3. **Seguro por design?** **Parcialmente** — validação e limites de upload são bons sinais; **perímetro da API e browser storage não são**.  
4. **Arquitetura sustentável?** **No núcleo, sim.** **Nos adaptadores e ops, até prova em contrário, não.**  
5. **Onde quebra primeiro?** **CLI** (conflitos/regressão) e **incidentes** (falta de logs) se a API sair do localhost.  
6. **O que impede nota 10/10?** God CLI, API sem observabilidade/auth, CI incompleto vs toolchain, E2E fraco no gate, política HTTP de dev “congelada” no código.  
7. **Caminho mínimo para excelência real?** Ver `docs/BRUTAL_REMEDIATION_PLAN.md` — em suma: **modularizar CLI**, **mypy+SCA no CI**, **logging estruturado na API**, **E2E crítico obrigatório**, **CORS/auth por ambiente ou gateway documentado**.

---

## Anexo: exemplo de classificação por achado (formato obrigatório)

*(Os restantes estão no backlog com a mesma granularidade.)*

| Campo | Exemplo: CLI monolítica |
|-------|-------------------------|
| Tipo | Architecture + Code |
| Severidade | ALTO |
| Impacto | Alto |
| Escopo | Sistémico |
| Frequência | Recorrente (cada feature nova) |
| Risco futuro | Alto |
| Root cause | Falta de modularização forçada por convenção/CI |
| Evidência | `apps/cli/otm_cli/cli.py` (~1272 linhas) |
| Recomendação | Quebrar em `commands/` + testes por comando; `cli.py` só bootstrap |

| Campo | Exemplo: API sem logging |
|-------|-------------------------|
| Tipo | DevOps + Architecture |
| Severidade | ALTO |
| Impacto | Alto (ops) |
| Escopo | Sistémico |
| Frequência | Recorrente (todos os endpoints) |
| Risco futuro | Alto |
| Root cause | Produto pensado como lib; plataforma não materializada |
| Evidência | `apps/api/` — ausência de `logging`/`logger` em grep |
| Recomendação | Middleware de request id + log estruturado JSON + níveis por rota |

---

*Auditoria estática. Não substitui pentest, DAST, nem revisão de configuração do hosting (CSP, TLS, WAF).*
