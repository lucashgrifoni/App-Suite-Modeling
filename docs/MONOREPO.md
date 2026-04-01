# Monorepo — estrutura e convenções

Este documento é o **mapa do repositório** para mantenedores e contribuidores. Objetivo: clareza, baixo acoplamento e crescimento sem caos.

---

## 1. Árvore de diretórios (completa)

```
.
├── .github/
│   └── workflows/          # CI/CD (ex.: testes Python, lint)
├── apps/
│   ├── api/                # Backend HTTP (FastAPI)
│   │   ├── Dockerfile
│   │   └── otm_api/
│   ├── cli/                # Linha de comando (Typer)
│   │   └── otm_cli/
│   └── web/                # Frontend (Vite + React + TS)
│       ├── src/
│       ├── index.html
│       ├── package.json
│       └── vite.config.ts
├── docs/
│   ├── adr/                # Architecture Decision Records
│   ├── ARCHITECTURE.md
│   ├── MVP_ROADMAP.md
│   ├── MONOREPO.md         # este arquivo
│   └── README.md
├── examples/               # Modelos TaC e snippets reproduzíveis
├── packages/               # Bibliotecas Python reutilizáveis (domínio)
│   ├── core-schema/        # Schema canônico (Pydantic), I/O YAML/JSON
│   ├── threat-engine/      # STRIDE, risco, geração de ameaças
│   ├── framework-mappings/ # OWASP, NIST, ISO — dados e funções puras
│   ├── exporters/          # Markdown, Mermaid, etc.
│   ├── diagram-engine/     # Grafo neutro para UI (React Flow)
│   └── industry-packs/     # Packs declarativos por setor (YAML)
├── tests/                  # Testes de integração e contratos (raiz)
├── docker-compose.yml
├── pyproject.toml          # Projeto Python e metadados
├── README.md
├── CONTRIBUTING.md
├── LICENSE
└── .gitignore
```

Pastas **opcionais** que podem surgir sem mudar a filosofia:

- `scripts/` — utilitários de manutenção (migração de schema, geração de docs).
- `infra/` — Terraform, Helm (se o deploy exigir; evitar até ser necessário).

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
| **`apps/api`** | Orquestração HTTP, autenticação (futuro), persistência (futuro). **Reutiliza** pacotes; não duplica regras do motor. |
| **`apps/cli`** | UX de terminal; **mesmo core** que a API. Comandos finos (`validate`, `export`, …). |
| **`apps/web`** | UI; **não** reimplementa STRIDE nem validação duplicada: chama API ou valida via contrato exposto (JSON Schema / endpoint). |
| **`examples/`** | Cenários mínimos e realistas para testes manuais e documentação. |
| **`docs/`** | Arquitetura, ADRs, roadmap, guia do monorepo. |
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
| `docs/ARCHITECTURE.md` | Visão técnica (já existente). |
| `docs/adr/` | Decisões importantes (ex.: schema canônico). |
| `.github/workflows/*` | CI mínimo verde. |

Recomendados em breve: `SECURITY.md` (como reportar vulnerabilidade), `CODE_OF_CONDUCT.md` (comunidade).

---

## 6. Princípios que mantêm o monorepo saudável

1. **Regra de dependência:** `apps/*` → `packages/*`; `packages/*` **não** importam `apps/*`.
2. **Core primeiro:** mudanças no schema passam por testes e, se possível, por exemplo em `examples/`.
3. **UI e CLI como clientes:** mesma validação e mesmos tipos conceituais; divergência = bug.
4. **Documentar decisões estruturais** em ADRs curtos, não só no chat.

Para a visão de produto e fases, ver [`MVP_ROADMAP.md`](MVP_ROADMAP.md).
