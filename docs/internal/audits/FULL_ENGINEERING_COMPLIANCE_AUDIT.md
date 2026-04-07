# Auditoria completa de conformidade de engenharia — App Suite Modeling

**Data:** 2026-04-06  
**Tipo:** auditoria **somente leitura** (sem alterações de código, regras de negócio ou arquitetura).  
**Escopo auditado:** repositório na íntegra com prioridade no **núcleo do produto** (`packages/*`, `apps/api`, `apps/cli`, `apps/web`, `tests`, `scripts`, `contracts`, `docs`, `.github`, exemplos, Docker).  
**Metodologia:**

1. Mapeamento estrutural e identificação de stack (Python 3.11+, FastAPI, Typer, React/Vite, Playwright no CI).  
2. Leitura de documentação declarativa (`ARCHITECTURE.md`, `KNOWN_LIMITATIONS.md`, `API.md` referenciados indiretamente).  
3. Inspeção dirigida por risco (auth, CORS, uploads, subprocess, storage browser, logging).  
4. Execução das ferramentas já previstas no CI ou disponíveis no ambiente (detalhe em `FULL_ENGINEERING_TOOL_EXECUTION_LOG.md`).  
5. Classificação de achados com severidade, evidência e limites de verificação.

---

## Stack identificada

| Camada | Tecnologias |
|--------|-------------|
| Linguagens | Python 3.11+; TypeScript (React 18) |
| Backend | FastAPI, Uvicorn, Pydantic v2, PyYAML |
| CLI | Typer, Rich |
| Frontend | Vite 5, Tailwind, React Flow, i18next, jsPDF |
| Testes | pytest (+ httpx), Vitest, Playwright (CI) |
| Contratos | OpenAPI versionado em `contracts/openapi.json` |
| Contentor | `Dockerfile` Python slim, utilizador não-root |
| CI | GitHub Actions: Python + Web + E2E + híbrido; Dependabot |

---

## Arquitetura percebida (declarada vs real)

**Declarada** (`docs/architecture/ARCHITECTURE.md`): monorepo com `otm_core_schema` como contrato canónico; `otm_threat_engine` sem HTTP; `otm_api` como adaptador HTTP; CLI e UI como clientes; diagram engine e exporters como serviços de suporte.

**Observada:**

- A API **importa e orquestra** pacotes de domínio sem reimplementar STRIDE no router — coerente.  
- Existe **enforcement mecânico** da fronteira core/adapters (`scripts/check_core_adapter_boundary.py` + testes) — forte aderência prática.  
- **SQLAlchemy** está nos extras `api` mas **não aparece** no código da aplicação API — desalinhamento menor entre dependências e código (ver achado AUD-ARCH-001).  
- A UI guarda estado de trabalho em **sessionStorage** — coerente com `KNOWN_LIMITATIONS.md` (sem persistência server-side).

**Conclusão arquitetural:** a arquitetura **real** segue em grande parte a **declarada**; os desvios são sobretudo **evolutivos** (BD futura) e **de empacotamento** (extra não usado), não uma segunda camada de domínio na UI.

---

## Resumo executivo

O projeto é um **monorepo maduro para threat modeling as code**, com **excelente cobertura de testes Python**, **contrato OpenAPI verificável no CI**, **auditoria de dependências Python** e **disciplina de import boundaries**. A documentação de **limitações** (sem auth, sem persistência central) é **alinhada com o código**, o que é raro e positivo.

Os principais **gaps** não são “código feio”, mas **maturidade de endurecimento para exposição pública**: API **sem autenticação** e **sem rate limiting**, **CORS permissivo em desenvolvimento**, e **ausência de SAST** (Bandit/Semgrep) e de **gate de formatação** no CI apesar de drift significativo (`ruff format --check` falharia). O frontend tem **typecheck limpo** mas **poucos testes unitários** TypeScript; a confiança na UI repousa mais em **E2E no CI** do em pirâmide unitária local.

**Nota geral composta (ver scorecard): ≈ 7.55 / 10.0**

---

## Nota por domínio

Ver `FULL_ENGINEERING_SCORECARD.md` para a tabela completa. Síntese:

| Domínio | Nota |
|---------|------|
| Clean Code | 7.2 |
| Clean Architecture | 7.8 |
| AppSec | 6.3 |
| Testes | 8.4 |
| Governança | 7.4 |
| Documentação | 8.8 |
| Frontend | 7.0 |
| Maturidade geral | 7.5 |

---

## Principais pontos fortes

1. **Testes e contratos:** 408 testes pytest passando na sessão de auditoria; verificação de OpenAPI; alinhamento TS/Python em vários testes de contrato.  
2. **Fronteira de domínio:** script e testes `core_adapter_boundary` — demonstra intenção verificável, não só texto em ADR.  
3. **Observabilidade prudente:** `observability.py` declara e cumpre não logar corpos de pedidos — reduz vazamento de dados de modelos.  
4. **Import de ficheiros:** limite explícito de 2 MiB em `routers/imports.py`.  
5. **Dockerfile:** execução como utilizador não privilegiado.  
6. **CI abrangente:** lint, mypy parcial, pip-audit, builds web em Linux e Windows, múltiplos jobs E2E.  
7. **Documentação extensa e honesta** sobre limitações de produto e segurança.  
8. **gitleaks** em modo git: sem leaks detetados no histórico analisado.

---

## Principais pontos fracos

1. **API pública implicitamente aberta** — sem camada de auth no código.  
2. **Sem rate limiting** na API — risco de abuso de compute.  
3. **Drift de formatação** em massa (73 ficheiros) sem gate CI correspondente.  
4. **Mypy** com `ignore_missing_imports` e âmbito limitado ao CI — buracos de garantia estática.  
5. **Pouca cobertura unitária TS** no front (2 ficheiros Vitest).  
6. **npm** reporta vulnerabilidades **moderadas** na cadeia Vite/esbuild (contexto dev).  
7. **Sem SAST** integrado (Bandit/Semgrep) e sem scan de imagem no workflow analisado.  
8. **CSP / headers de segurança** não evidenciados na configuração Vite analisada.

---

## Achados críticos (lista curta)

Nesta auditoria **não foi confirmada** uma vulnerabilidade tipo “RCE remota” ou “segredo commitado” no histório git analisado.

Os itens abaixo são **críticos ou altos no contexto de uso indevido** (ex.: API na Internet aberta):

| ID | Tema | Porque é grave |
|----|------|----------------|
| AUD-APPSEC-001 | API sem auth | Exposição pública = qualquer um consome análise e submete dados sensíveis de threat model. |
| AUD-APPSEC-002 | Sem rate limiting | Amplifica DoS e custo operacional. |

*Se o uso for **estritamente local** ou atrás de gateway corporativo, a severidade **efetiva** desce — mas aí o controlo é **externo ao repo**.*

---

## Riscos estruturais

1. **Complexidade crescente** no `otm_threat_engine` e dados em `industry-packs` — revisões humanas mais caras; mitigado por testes, não eliminado.  
2. **Dependência opcional não usada** (SQLAlchemy) — pequena dívida de clareza para novos contribuintes.  
3. **Formatação inconsistente** — atrito em revisões e merges sem `ruff format` gate.

---

## Riscos de segurança

1. **Modelo de ameaça da implantação** deve assumir: payloads podem conter **informação confidencial** sobre sistemas reais; sem TLS/auth no servidor, **confidencialidade e integridade** dependem inteiramente da rede e do cliente.  
2. **XSS** não foi confirmado; superfície típica seria renderização insegura — há comentário explícito em `diagramSanitize.ts` sobre evitar `dangerouslySetInnerHTML`; **não** foi feita auditoria manual completa de todos os componentes React.  
3. **CORS + credentials** — configurável; em produção sem origens, browsers bloqueiam cross-origin credentialed — comportamento defensivo **se** `OTM_ENV` e `OTM_CORS_ORIGINS` estiverem corretos.

---

## Áreas não verificáveis ou parcialmente verificáveis

1. **Todas as linhas de código** — amostragem + ferramentas globais.  
2. **Suíte Playwright completa** — **não reexecutada** nesta máquina; confiança **derivada do CI**.  
3. **`gitpage/`** — marketing; build/test não corridos.  
4. **`docker-compose` em runtime** — não levantado.  
5. **Semgrep / Bandit / Trivy / Checkov** — não integrados ou não executados com sucesso nesta sessão (ver log de ferramentas).  
6. **gitleaks --no-git** sem ignorar `.venv` — gera falsos positivos; não usado como evidência de segredo real.

---

## Conclusão brutal e honesta

**O que está aderente**

- Separação **razoável** entre domínio (schema + engine) e adaptadores (API/CLI).  
- **Testes de backend e de contrato** num patamar **acima da média** de projetos open source comparáveis.  
- **CI** com supply chain Python auditada no pipeline e **npm audit** para critical.  
- **Documentação** que **não mente** sobre auth e persistência.

**O que está parcialmente aderente**

- **Clean Code** no sentido “uniformidade”: lint OK, formatação **não** canónica em muitos ficheiros.  
- **AppSec**: boas práticas **parciais** (limites de upload, logging contido) mas **sem** controles de identidade, abuso ou edge security completos **no código**.  
- **Frontend**: TypeScript rigoroso; testes unitários **finos**.  
- **Type safety** Python: mypy **só** onde o CI manda, com config permissiva.

**O que está não aderente** (a critérios enterprise de “API segura na Internet por omissão”)

- **Não** existe autenticação nem autorização na API.  
- **Não** existe rate limiting.  
- **Não** existe pipeline SAST obrigatório no repositório analisado.

**Maiores riscos arquiteturais**

- Evolução do motor e dos packs sem quebra de fronteiras (hoje **mitigada** por testes + boundary check).  
- Drift de formatação e tipagem parcial podem **acelerar erros** em refatorações grandes.

**Maiores riscos de segurança**

- **Implantação pública ingénua** da API (sem gateway) — **alto risco**.  
- **Dependência de dev** (Vite/esbuild) com CVEs moderadas — risco **contextual** (principalmente dev server).

**O que impede considerar o projeto “maduro” no sentido enterprise de AppSec**

- Falta de **identidade**, **limite de taxa** e **hardening HTTP** no produto entregue, compensados apenas por documentação e implantação externa.  
- Falta de **SAST** e de **format gate** alinhados à qualidade já demonstrada nos testes.

**Nota real hoje**

- **~7.5/10** como engenharia de produto open-source com motor complexo.  
- **Não** é 9/10 para **exposição pública desprotegida**.

**Pode confiar estruturalmente?**

- **Sim**, para **integridade do desenho modular e regressão funcional**, dado o estado dos testes e do CI **observados**.  
- **Não** para **confiar na segurança perimetral da API** sem camadas externas — o próprio repositório **admite** isso em `KNOWN_LIMITATIONS.md`.

---

## Decisão final de aderência

**Classificação:** **parcialmente aderente**

**Leitura executiva (rótulos pedidos):**

- **Estruturalmente pronto** para evolução contínua **com** a disciplina de testes atual.  
- **Razoável mas com gaps sérios** se o objetivo for **SaaS público** sem trabalho adicional de segurança.  
- **Não “frágil”** no sentido de ausência de testes — a fragilidade está no **perímetro de segurança** e em **gates de estilo/SAST**.  
- **Arriscado para escalar** como **serviço multi-tenant aberto** sem auth, DB e políticas de dados.  
- **Tecnicamente maduro** na **camada de domínio e verificação**; **tecnicamente inconsistente** na **uniformidade de formatação** e **cobertura estática/mypy**.  
- **Seguro o suficiente para o estágio atual** **se** o estágio for **ferramenta local / rede de confiança / atrás de controlo explícito** — como documentado.  
- **Inseguro para o estágio atual** **se** o estágio for **API exposta à Internet sem compensações**.

---

## Artefactos relacionados

| Ficheiro | Conteúdo |
|----------|----------|
| `FULL_ENGINEERING_FINDINGS_MATRIX.md` | IDs, severidades, evidências |
| `FULL_ENGINEERING_SCORECARD.md` | Notas e risco |
| `FULL_ENGINEERING_FILE_COVERAGE.md` | Cobertura por pasta |
| `FULL_ENGINEERING_TOOL_EXECUTION_LOG.md` | Comandos e resultados |
| `FULL_ENGINEERING_NEXT_ACTIONS.md` | Plano não executado |

---

*Auditoria concluída sem modificações ao código-fonte.*
