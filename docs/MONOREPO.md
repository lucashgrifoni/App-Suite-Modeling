# Monorepo — estrutura e convenções

Este documento é o **mapa do repositório** para mantenedores e contribuidores. Objetivo: clareza, baixo acoplamento e crescimento sem caos.

---

## 1. Árvore de diretórios (completa)

Mapa lógico detalhado (camadas × domínios): ver também [`REPOSITORY_LAYOUT.md`](REPOSITORY_LAYOUT.md) e a narrativa de produto em [`PROJECT_DEEP_DIVE.md`](PROJECT_DEEP_DIVE.md).

```
.
├── .github/
│   └── workflows/          # CI/CD: Python (ruff, mypy, pytest, bandit, semgrep, trivy…), web, E2E
├── apps/
│   ├── api/                # Backend HTTP (FastAPI), OpenAPI, perímetro opcional
│   │   ├── Dockerfile
│   │   └── otm_api/
│   ├── cli/                # Linha de comando (Typer) — ponto de entrada `otm`
│   │   └── otm_cli/
│   └── web/                # Frontend (Vite + React + TS)
│       ├── src/
│       ├── index.html
│       ├── package.json
│       └── vite.config.ts
├── contracts/              # Contratos / snapshots usados pelo projeto (ex.: OpenAPI)
├── docs/
│   ├── README.md           # Índice principal da documentação
│   ├── MONOREPO.md         # este arquivo
│   ├── REPOSITORY_LAYOUT.md
│   ├── PROJECT_DEEP_DIVE.md
│   ├── KNOWN_LIMITATIONS.md
│   ├── VERSIONING_AND_TAGS.md
│   ├── CI_AND_SECURITY_EVIDENCE.md
│   ├── DOCUMENTATION_STRUCTURE.md  # mapa editorial público vs interno
│   ├── features/           # Guias de produto e superfícies (CLI, API, UI, imports…)
│   ├── architecture/       # ADRs, deployment, contratos CI, políticas de tooling
│   │   └── adr/
│   ├── internal/           # Auditorias, relatórios, checklists de release (mantenedores)
│   │   ├── audits/
│   │   ├── reports/
│   │   ├── logs/
│   │   ├── decisions/
│   │   └── checklists/
│   └── screenshots/
├── examples/               # Modelos TaC e snippets reproduzíveis
├── fixtures/               # Dados de teste partilhados (quando existirem)
├── gitpage/               # Site estático (GitHub Pages), build Vite separado de apps/web
├── packages/               # Bibliotecas Python reutilizáveis (domínio); ver pyproject packages.find
│   ├── core-schema/        # Schema canônico (Pydantic), I/O YAML/JSON
│   ├── explainability/     # Contratos / utilitários de explicabilidade
│   ├── threat-engine/      # Multi-metodologia, STRIDE, lentes, PLOT4ai, heurísticas
│   ├── framework-mappings/ # OWASP, NIST, ISO — dados e funções puras
│   ├── exporters/          # Markdown, Mermaid, bundle, etc.
│   ├── diagram-engine/     # Grafo neutro para UI (React Flow)
│   ├── industry-packs/     # Packs declarativos por setor (YAML)
│   ├── artifact-import/    # Import OpenAPI, K8s, Terraform, Helm…
│   └── report-premium/     # Relatório premium (extra [report])
├── scripts/                # Setup, verificação OpenAPI, gates; no pythonpath do pytest
├── tests/                  # Suite principal na raiz
├── docker-compose.yml
├── pyproject.toml          # Projeto Python e metadados (versão open-threat-model)
├── README.md
├── CONTRIBUTING.md
├── LICENSE
└── .gitignore
```

Outras pastas comuns **geradas** ou ignoradas: `artifacts/`, `build/`, `dist/`, `.coverage`, `htmlcov/` — não versionar.

Pastas **opcionais** além das acima:

- `infra/` — Terraform, Helm dedicados ao deploy (se o projeto crescer para infra própria na raiz).

---

## 2. Responsabilidade de cada pasta

| Pasta | Responsabilidade |
|--------|------------------|
| **`packages/*`** | **Domínio e bibliotecas**: sem dependência de HTTP ou React. Consomem e produzem tipos do core (`otm_core_schema`) ou estruturas derivadas. |
| **`packages/core-schema`** | Contrato canônico, validação, serialização. **Fonte da verdade** para o que é um “documento OTM” válido. |
| **`packages/threat-engine`** | Análise (STRIDE, trust boundaries, score). **Não** conhece FastAPI nem Typer. |
| **`packages/framework-mappings`** | Mapeamentos para normas/frameworks; dados versionados + funções puras. |
| **`packages/exporters`** | Transformação documento → artefatos (MD, Mermaid). Sem side effects ocultos no modelo. |
| **`packages/diagram-engine`** | Documento → nós/arestas para diagramação (compartilhável com a UI). |
| **`packages/industry-packs`** | Conteúdo declarativo (YAML) por setor; carregado e validado contra o schema. |
| **`packages/explainability`** | Explicabilidade estruturada alinhada ao motor e consumo por API/CLI/UI. |
| **`packages/artifact-import`** | Conversão de artefatos de engenharia (OpenAPI, K8s, Terraform, Helm…) em rascunho canônico. |
| **`packages/report-premium`** | Relatórios premium (MD/HTML/PDF) com extras opcionais de dependência. |
| **`apps/api`** | Orquestração HTTP, autenticação (futuro), persistência (futuro). **Reutiliza** pacotes; não duplica regras do motor. |
| **`apps/cli`** | UX de terminal; **mesmo core** que a API. Comandos finos (`validate`, `export`, …). |
| **`apps/web`** | UI; **não** reimplementa STRIDE nem validação duplicada: chama API ou valida via contrato exposto (JSON Schema / endpoint). |
| **`examples/`** | Cenários mínimos e realistas para testes manuais e documentação. |
| **`docs/`** | Hub de documentação: núcleo na raiz de `docs/`, guias em `features/`, engenharia em `architecture/`, material operacional em `internal/` (ver `DOCUMENTATION_STRUCTURE.md`). |
| **`tests/`** | Testes que cruzam pacotes ou validam exemplos; testes unitários podem viver ao lado do código (`tests/` dentro do pacote) se o time preferir — hoje a raiz centraliza. |
| **`.github/workflows`** | Automação: instalar deps, `ruff`, `pytest` (e no futuro build web). |

---

## 3. Convenções de nomes

### Repositório e artefatos

- **Nome do projeto PyPI/dist:** `open-threat-model` (kebab-case no `pyproject.toml`).
- **Imports Python:** prefixo `otm_` + domínio em **snake_case**: `otm_core_schema`, `otm_threat_engine`, `otm_cli`, `otm_api`.
- **Pastas de pacote (disco):** kebab-case (`core-schema`, `threat-engine`) — legível em URLs e terminais; o **nome de import** continua Pythonico (`otm_*`).
- **Arquivos de modelo TaC:** sufixo sugerido `.otm.yaml` ou `.otm.yml` (documentação e exemplos).

### Código

- **Python:** PEP 8, `snake_case` para funções/variáveis, `PascalCase` para modelos Pydantic.
- **TypeScript/React:** `PascalCase` para componentes; arquivos `ComponentName.tsx`.
- **Chaves no YAML canônico:** `snake_case` alinhado ao `ThreatModelDocument` (com alias documentado, ex.: `model` no arquivo).

### Branches e commits (sugestão para OSS)

- Branches: `feat/…`, `fix/…`, `docs/…`, `chore/…`.
- Commits: estilo [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`) — facilita changelog automático depois.

---

## 4. Estratégia de packaging (recomendada)

### Estado atual (MVP): **um `pyproject.toml` na raiz**

- **Um único pacote de distribuição** `open-threat-model` que inclui todos os `otm_*` via `setuptools` `packages.find` em `packages/*` e `apps/cli`, `apps/api`.
- **Extras opcionais:** `[api]`, `[cli]`, `[dev]` para não obrigar quem só quer o core a instalar FastAPI/Typer.

**Vantagens:** instalação simples (`pip install -e ".[dev,cli,api]"`), um versionamento, CI trivial.

**Quando evoluir:** se um pacote precisar ser publicado **isoladamente** no PyPI (ex.: só `otm_core_schema`), aí sim extrair para `packages/core-schema/pyproject.toml` próprio ou usar **uv workspace** / Poetry workspace — **somente quando houver demanda real**, para não multiplicar complexidade cedo demais.

### Frontend

- **`apps/web`** é um projeto **Node** independente (`package.json`), instalado com `npm install` / `pnpm install`.
- Contrato com o backend: **OpenAPI** + tipos gerados (fase posterior) ou fetch tipado manual no MVP.

### Docker

- Imagem da API a partir do contexto da raiz (`Dockerfile` em `apps/api/`), copiando `packages/` e `apps/api/` — uma imagem por app é suficiente no início.

---

## 5. Arquivos iniciais obrigatórios (checklist OSS)

| Arquivo | Função |
|---------|--------|
| `README.md` | O quê é o projeto, como rodar em 5 minutos, links para docs. |
| `LICENSE` | Licença explícita (ex.: MIT). |
| `CONTRIBUTING.md` | Como configurar ambiente, padrão de PR, estilo de código. |
| `pyproject.toml` | Metadados Python, dependências, scripts, ferramentas (ruff, pytest). |
| `.gitignore` | Artefatos de build, venv, node_modules, caches. |
| `docs/architecture/ARCHITECTURE.md` | Visão técnica (já existente). |
| `docs/architecture/adr/` | Decisões importantes (ex.: schema canônico). |
| `.github/workflows/*` | CI mínimo verde. |

Presentes na raiz: [`SECURITY.md`](../SECURITY.md) (como reportar vulnerabilidade), [`CODE_OF_CONDUCT.md`](../CODE_OF_CONDUCT.md) (comunidade) e [`CONTRIBUTING.md`](../CONTRIBUTING.md) (como contribuir).

---

## 6. Princípios que mantêm o monorepo saudável

1. **Regra de dependência:** `apps/*` → `packages/*`; `packages/*` **não** importam `apps/*`.
2. **Core primeiro:** mudanças no schema passam por testes e, se possível, por exemplo em `examples/`.
3. **UI e CLI como clientes:** mesma validação e mesmos tipos conceituais; divergência = bug.
4. **Documentar decisões estruturais** em ADRs curtos, não só no chat.

Para o registo histórico das fases que levaram ao MVP, ver [`features/MVP_ROADMAP.md`](features/MVP_ROADMAP.md) — não é o roadmap actual.
