# Catálogo de templates

Os templates são **pontos de partida**: documentos canónicos válidos com componentes, fluxos e fronteiras de confiança mínimos. Devem ser revistos pelo modelo de ameaças do projeto; não substituem workshops completos nem garantem cobertura total.

## Categorias

| Chave | Rótulo UI |
|-------|-----------|
| `applications` | Applications |
| `cloud_infra` | Cloud & Infra |
| `identity_access` | Identity & Access |
| `integrations` | Integrations |
| `ai_llm` | AI & LLM |
| `industry` | Industry |
| `objective` | Objective-based |

## UI

Na página **Templates**, filtre por texto (debounce), categoria, complexidade e tag exata. Os cartões mostram ID, categoria, complexidade opcional, pack sugerido, metodologia sugerida e “ideal para”.

## API

- `GET /v1/templates` — lista completa. Query opcional: `category`, `tag`, `complexity`, `q`.
- `GET /v1/templates/{template_id}` — metadados de um template.
- `POST /v1/templates/{template_id}/instantiate` — documento canónico pronto a editar.

## CLI

```bash
otm templates                    # lista (comportamento por omissão)
otm templates list [--category ...] [--tag ...] [--complexity ...] [--query ...]
otm templates show api-public
otm init -t ai-rag-enterprise threatmodel.otm.yaml
otm init --list-templates
```

## Limitações

- Templates não incluem ameaças pré-preenchidas; o motor e os packs continuam a aplicar-se após análise.
- Metadados de “metodologia sugerida” orientam recomendação e documentação; o utilizador pode alterar no modelo.

## Como adicionar um template novo

1. Acrescentar uma entrada em `packages/industry-packs/otm_industry_packs/catalog/registry_data.py` (`EXPANSION_TEMPLATE_SPECS`).
2. Executar `python scripts/emit_template_catalog.py` na raiz (com `packages/core-schema` e `packages/industry-packs` no path, como no script).
3. Correr `pytest tests/test_template_catalog_expansion.py` e a suíte completa.
