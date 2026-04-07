# Layout do repositório — camadas, domínios e responsabilidades

Este documento complementa [`MONOREPO.md`](MONOREPO.md) com um **mapa lógico**: onde vive cada responsabilidade, como as pastas se relacionam e **por que** a estrutura física atual é mantida (evitar quebras de packaging e CI).

---

## 1. Princípio de organização

| Eixo | O que significa neste projeto |
|------|-------------------------------|
| **Camada** | *Presentation* (`apps/web`), *delivery* HTTP (`apps/api`), *delivery* CLI (`apps/cli`), *domínio* (`packages/*`), *contratos e exemplos* (`contracts/`, `examples/`), *automação* (`scripts/`, `.github/`). |
| **Domínio / feature** | Cada pacote `packages/<nome>` corresponde a um **bounded context** Python (`otm_*`): schema, motor de ameaças, importação de artefatos, exportadores, diagrama, packs, explainability, relatório premium. |
| **Fonte da verdade** | O **documento canônico** (modelo Pydantic em `otm_core_schema`) é a raiz; apps apenas orquestram e expõem o mesmo comportamento. |

**Regra de dependência (não negociável):** `apps/*` → `packages/*`; pacotes **não** importam `apps/*`.

---

## 2. Árvore física alinhada ao `pyproject.toml`

A distribuição única **`open-threat-model`** declara pacotes em:

- `packages/core-schema`, `explainability`, `threat-engine`, `framework-mappings`, `exporters`, `diagram-engine`, `industry-packs`, `artifact-import`, `report-premium`
- `apps/cli`, `apps/api`

Qualquer **movimentação física** desses caminhos exige atualizar `tool.setuptools.packages.find`, `tool.pytest.ini_options.pythonpath`, Docker, CI e imports — por isso a “organização por pasta” é **documentada aqui** como contrato, não como refactor estrutural arbitrário.

```
.
├── .github/workflows/     # CI: Python (ruff, mypy, pytest, bandit, semgrep, trivy…), web (npm), E2E
├── apps/
│   ├── api/otm_api/       # FastAPI: REST, OpenAPI, perímetro opcional (API key, rate limit)
│   ├── cli/otm_cli/       # Typer: validate, analyze, export, import, diff, relatórios…
│   └── web/               # Vite + React + TS: wizard, diagrama, análise, export, i18n
├── packages/
│   ├── core-schema/       # otm_core_schema — schema canônico, I/O YAML/JSON
│   ├── threat-engine/     # otm_threat_engine — STRIDE, lentes metodológicas, heurísticas, PLOT4ai
│   ├── explainability/  # otm_explainability — contratos de explicabilidade (se aplicável ao core)
│   ├── framework-mappings/
│   ├── exporters/
│   ├── diagram-engine/
│   ├── industry-packs/
│   ├── artifact-import/   # OpenAPI, K8s, Terraform, Helm… → rascunho canônico
│   └── report-premium/    # Relatórios premium (MD/HTML/PDF via extra `[report]`)
├── scripts/               # setup, verificação OpenAPI, gates locais (também no pythonpath pytest)
├── tests/                 # Suite principal de testes na raiz
├── examples/              # Modelos `.otm.yaml` e cenários reproduzíveis
├── fixtures/              # Dados de teste compartilhados (quando existirem)
├── contracts/             # Artefatos de contrato (ex.: snapshots OpenAPI) conforme uso do repo
├── gitpage/               # Site estático Vite para GitHub Pages (pipeline dedicada)
├── docs/                  # Arquitetura, ADRs, guias operacionais, evidência de CI/segurança
├── docker-compose.yml
├── pyproject.toml
└── README.md
```

Pastas como `artifacts/`, `build/`, `dist/`, `.coverage` são **geradas** ou ignoradas pelo `.gitignore` — não fazem parte do contrato de código-fonte.

---

## 3. Matriz camada × responsabilidade

| Camada | Pastas | Papel |
|--------|--------|--------|
| **Interface web** | `apps/web` | UX; chama API; não duplica regras STRIDE/validação do servidor além do que o produto exige para UX. |
| **API HTTP** | `apps/api` | Validação de payloads, orquestração, headers/CORS, observabilidade, limites de taxa. |
| **CLI** | `apps/cli` | Mesmos casos de uso que a API, orientados a terminal e automação. |
| **Domínio** | `packages/*` | Lógica pura de threat modeling, importação, exportação, dados versionados. |
| **Qualidade / entrega** | `.github`, `scripts`, `tests` | Gates reprodutíveis e documentação de evidência em `docs/CI_AND_SECURITY_EVIDENCE.md`. |

---

## 4. Domínios Python (`otm_*`)

| Pacote (pasta) | Módulo importável | Função principal |
|----------------|-------------------|------------------|
| `core-schema` | `otm_core_schema` | Modelo canônico `ThreatModelDocument`, validação, serialização. |
| `threat-engine` | `otm_threat_engine` | Análise multi-metodologia, recomendações, corpus/sinais (ex. PLOT4ai). |
| `explainability` | `otm_explainability` | Estruturas de explicação alinhadas ao motor / contratos. |
| `framework-mappings` | `otm_framework_mappings` | Mapeamentos OWASP/NIST/ISO (dados + funções). |
| `exporters` | `otm_exporters` | Documento → Markdown, Mermaid, JSON bundle, etc. |
| `diagram-engine` | `otm_diagram_engine` | Projeção grafo ↔ UI. |
| `industry-packs` | `otm_industry_packs` | Packs YAML por setor. |
| `artifact-import` | `otm_artifact_import` | Ingestão de artefatos de engenharia → modelo draft. |
| `report-premium` | `otm_report_premium` | Pipeline de relatório premium (extras `[report]`). |

---

## 5. Onde encontrar quê (atalhos)

- **Schema e evolução:** [`SCHEMA_V1.md`](features/SCHEMA_V1.md), `packages/core-schema/`.
- **Motor e metodologias:** [`CORE_ENGINE.md`](features/CORE_ENGINE.md), [`MULTI_ENGINE_ARCHITECTURE.md`](features/MULTI_ENGINE_ARCHITECTURE.md), `packages/threat-engine/`.
- **Importação:** [`ARTIFACT_IMPORT.md`](features/ARTIFACT_IMPORT.md), `packages/artifact-import/`.
- **API e perímetro:** [`API.md`](features/API.md), [`DEPLOYMENT_INVARIANTS.md`](architecture/DEPLOYMENT_INVARIANTS.md).
- **Produto e narrativa profunda:** [`PROJECT_DEEP_DIVE.md`](PROJECT_DEEP_DIVE.md).
- **Mapa da pasta `docs/`:** [`DOCUMENTATION_STRUCTURE.md`](DOCUMENTATION_STRUCTURE.md).

---

*Última revisão alinhada à versão do pacote em `pyproject.toml` e à lista `packages.find`.*
