# Pacotes Python (`packages/`)

Bibliotecas **reutilizáveis** consumidas por CLI, API e (indiretamente) pela UI via API.

| Pacote (import) | Conteúdo esperado |
|-----------------|-------------------|
| `otm_core_schema` | Modelo canônico, validação, YAML/JSON |
| `otm_threat_engine` | STRIDE, risco, heurísticas de fronteira de confiança |
| `otm_framework_mappings` | Mapeamentos OWASP/NIST/ISO |
| `otm_exporters` | Saídas Markdown, Mermaid, … |
| `otm_diagram_engine` | Grafo para diagramas |
| `industry-packs/` | `otm_industry_packs` — templates `.otm.yaml` e packs por setor (YAML + loader) |

**Regra:** nada aqui depende de FastAPI, Typer ou React.
