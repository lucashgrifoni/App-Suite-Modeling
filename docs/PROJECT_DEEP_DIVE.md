# App Suite Modeling — mergulho profundo no produto e na engenharia

Este texto descreve **o que** é o projeto, **para quem** serve, **como** os componentes colaboram e **por que** as decisões técnicas fazem sentido num contexto de AppSec e DevSecOps. É o complemento narrativo ao [`README.md`](../README.md) e ao mapa em [`REPOSITORY_LAYOUT.md`](REPOSITORY_LAYOUT.md).

---

## 1. Definição em uma frase

**App Suite Modeling** é uma plataforma open source de *threat modeling as code*: um **modelo canônico versionado** (YAML/JSON) descreve arquitetura, fluxos e limites de confiança; sobre esse modelo rodam **várias metodologias de análise** (STRIDE, LINDDUN, PASTA, NIST Data-Centric, OCTAVE Allegro, CIA-DIE, PLOT4ai para sistemas de IA/LLM); os resultados incluem **ameaças estruturadas**, **explicabilidade**, **sugestões de backlog** e **artefatos exportáveis** consumíveis por humanos e por pipeline — expostos por **CLI**, **API REST** e **interface web**.

---

## 2. Problema de negócio e técnico

### 2.1 O que costumava falhar nos modelos ad hoc

- Diagramas e planilhas **divergem** do código e da infraestrutura real.
- Regras de análise ficam **presas** a uma ferramenta proprietária ou a um único framework (ex. só STRIDE).
- Equipes de entrega precisam de **gates repetíveis** (validar modelo, gerar relatório, comparar revisões), mas não têm um **contrato estável** em arquivo texto.
- Auditorias pedem **rastreabilidade** (por que esta ameaça apareceu?) — o projeto trata **explicabilidade** como cidadã de primeira classe, não como texto solto.

### 2.2 O que este projeto oferece

- **Single source of truth:** o documento OTM validado contra `otm_core_schema`.
- **Multi-superfície:** mesma lógica acessível por terminal, HTTP e browser.
- **Evolução disciplinada:** schema versionado, testes na raiz `tests/`, contratos OpenAPI verificados, diff semântico entre versões do modelo.
- **Integração com engenharia real:** importação assistida a partir de OpenAPI, Kubernetes, Terraform, Helm (e extensível), reduzindo fricção entre “documento de ameaças” e “o que está no Git”.

---

## 3. Arquitetura conceitual

### 3.1 Três anéis

1. **Núcleo (domínio)** — Pacotes `packages/*`: sem dependência de FastAPI, Typer ou React. Produzem estruturas de dados puras ou funções com side effects explícitos apenas onde necessário (ex. I/O de arquivo na CLI, não no core).
2. **Entrega** — `apps/api` e `apps/cli` orquestram validação, chamadas ao motor, export e import.
3. **Experiência** — `apps/web` guia o utilizador, visualiza diagramas (React Flow), consome a API e gera PDF no cliente quando aplicável.

### 3.2 Fluxo típico de valor

```text
(Import opcional) → Editar modelo canónico → Validar → Analisar (metodologia) → Rever explicações / backlog → Exportar ou Diff → Guardar no Git / pipeline
```

Cada seta corresponde a **comandos CLI** e/ou **endpoints HTTP** documentados em [`CLI.md`](features/CLI.md) e [`API.md`](features/API.md).

---

## 4. O documento canônico (coração do sistema)

### 4.1 Papel do `otm_core_schema`

- Define **entidades** (componentes, fluxos de dados, fronteiras de confiança, metadados).
- Garante **integridade** via Pydantic: o mesmo objeto em memória serve para API, CLI e testes.
- Permite **evolução controlada** do schema (campos novos, deprecações) com testes de regressão.

### 4.2 Por que YAML/JSON e não só diagrama

Texto estruturado permite:

- **Review** em pull request.
- **Diff** semântico (ver [`THREAT_MODEL_DIFF.md`](features/THREAT_MODEL_DIFF.md)).
- Geração determinística de relatórios e sincronização com outras ferramentas.

---

## 5. Motor de ameaças (`otm_threat_engine`)

### 5.1 Multi-metodologia

O motor não está preso a STRIDE: **lentes** ou perfis metodológicos aplicam regras e catálogos coerentes com cada framework escolhido ou recomendado (ver [`MULTI_ENGINE_ARCHITECTURE.md`](features/MULTI_ENGINE_ARCHITECTURE.md) e [`CHOOSE_METHODOLOGY.md`](features/CHOOSE_METHODOLOGY.md)).

### 5.2 PLOT4ai e sistemas de IA

Para componentes e fluxos relacionados a ML/LLM, existe um trilho especializado (sinais, heurísticas, blocos de explicação) documentado em [`PLOT4AI_AI_SYSTEM.md`](features/PLOT4AI_AI_SYSTEM.md). Isto alinha o produto a **governança de IA** e a modelos de ameaça contemporâneos, sem abandonar o mesmo documento canônico.

### 5.3 Explainability

Saídas incluem registos explicáveis (ver [`EXPLAINABILITY.md`](features/EXPLAINABILITY.md)): úteis para **auditoria**, formação e para afinar falsos positivos ao longo do tempo.

---

## 6. Importação de artefatos (`otm_artifact_import`)

Objetivo: **semear** ou **acelerar** o modelo a partir de fontes que as equipas já mantêm.

- **OpenAPI/Swagger** → superfícies HTTP e fluxos implícitos.
- **Kubernetes** → workloads, serviços, exposição de rede.
- **Terraform / Helm** → infraestrutura declarativa.

O resultado é normalmente um **rascunho** sujeito a validação humana — import não substitui o raciocínio de arquitetura, mas **reduz o tempo** até um modelo analisável.

---

## 7. Exportadores e relatório premium

- **Exportadores standard** (Markdown, Mermaid, bundles JSON) residem em `packages/exporters`.
- **Relatório premium** (`packages/report-premium`, extra `[report]`) adiciona formatos ricos (HTML/PDF via dependências opcionais) com suporte a **localização** (pt-BR/en) alinhado a [`I18N.md`](features/I18N.md).

---

## 8. API e CLI como simetría

- A API expõe **OpenAPI** estável; a web pode gerar tipos a partir desse contrato.
- A CLI expõe os **mesmos casos de uso** para CI: por exemplo validar um ficheiro em cada push, ou gerar um relatório como artefato de build.

Comandos de entrada: `otm` (ver `project.scripts` no `pyproject.toml`).

---

## 9. Interface web

- **Wizard** e fluxos guiados** reduzem barreira para novos utilizadores.
- **Diagrama** (React Flow) oferece edição visual; o estado consistente com o modelo canónico é obtido via API/sincronização conforme desenhado no produto.
- **Internacionalização** (i18n) cobre UI e artefatos exportados quando aplicável.

Detalhes de UX e integração: [`UI.md`](features/UI.md).

---

## 10. Segurança, confiança e exploração responsável

### 10.1 Modelo de confiança da API

A API foi pensada para **desenvolvimento e ambientes internos**; o perímetro opcional (`OTM_API_KEY`, rate limiting) está documentado em [`API.md`](features/API.md) e [`DEPLOYMENT_INVARIANTS.md`](architecture/DEPLOYMENT_INVARIANTS.md). **Exposição pública** exige camadas adicionais (gateway, OAuth/OIDC, persistência multi-tenant — itens de roadmap).

### 10.2 Pipeline de software seguro

- Lint/format (Ruff), tipos (mypy), testes (pytest), SAST (Bandit, Semgrep), SCA (pip-audit, npm audit), análise de imagem (Trivy), segredos (Gitleaks).
- Evidência consolidada: [`CI_AND_SECURITY_EVIDENCE.md`](CI_AND_SECURITY_EVIDENCE.md).

---

## 11. Testes e qualidade

- Testes de Python centralizados em `tests/` com `pythonpath` apontando para todos os pacotes e `scripts`.
- Front-end: Vitest, Playwright (E2E), conforme `apps/web`.
- **Links internos** em Markdown da documentação são validados por `tests/test_docs_links.py` para evitar documentação sincopada.

---

## 12. Estado do produto e roadmap

- Registo histórico das fases e critérios do MVP (já entregues): [`MVP_ROADMAP.md`](features/MVP_ROADMAP.md).
- Limitações honestas: [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md).
- Congelamentos e escopo: [`RELEASE_SCOPE_FREEZE.md`](internal/decisions/RELEASE_SCOPE_FREEZE.md), [`ENGINEERING_CLOSEOUT_SCOPE.md`](internal/decisions/ENGINEERING_CLOSEOUT_SCOPE.md).

---

## 13. Glossário rápido

| Termo | Significado |
|--------|-------------|
| **OTM** | *Open Threat Model* — família de artefatos e código `otm_*`. |
| **Documento canónico** | Instância validada de `ThreatModelDocument` (YAML/JSON). |
| **Lente / metodologia** | Conjunto de regras e categorias (STRIDE, LINDDUN, …). |
| **Import** | Transformação de artefacto externo em modelo draft OTM. |
| **Diff semântico** | Comparação estruturada entre duas revisões do modelo, não só texto. |

---

*Documento vivo: atualizar quando o `pyproject.toml` ou os pacotes listados em `setuptools.packages.find` mudarem.*
