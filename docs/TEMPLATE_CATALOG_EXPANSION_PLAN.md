# Plano — expansão do catálogo de templates

## Objetivo

Aumentar o catálogo embutido com **35 templates** (IDs estáveis) cobrindo aplicações, cloud, identidade, integrações, IA, setores e objetivos, **sem** criar motor paralelo, **sem** duplicar montagem de drafts em vários sítios e **sem** empurrar regras de negócio para a UI.

## Diagnóstico (estado antes da expansão)

- Artefactos: `packages/industry-packs/otm_industry_packs/data/templates/*.otm.yaml` + opcional `*.meta.json`.
- Metadados mínimos em `TemplateInfo` (id, title, description, suggested_pack).
- API: `GET /v1/templates`, `POST /v1/templates/{id}/instantiate`.
- CLI: `otm templates` listava IDs; `otm init -t ID`.
- UI: lista com filtro de texto local.

## Gaps endereçados

1. **Metadados** — categoria, tags, complexidade, best_for, metodologia sugerida, sinais para recomendação futura.
2. **Filtros** — servidor (API) e cliente (CLI) com a mesma semântica via `template_query.py`.
3. **Detalhe** — `GET /v1/templates/{template_id}` e `otm templates show ID`.
4. **Fonte única para YAML** — `catalog/registry_data.py` + `scripts/emit_template_catalog.py` gera os ficheiros validados contra o schema canónico.
5. **UI** — filtros por categoria, complexidade e tag exata; texto com debounce; cartões com metadados curtos.

## Estratégia de implementação

| Fase | Entrega |
|------|---------|
| Core | `TemplateInfo` estendido; `template_query.py`; 35 specs em `registry_data.py`; emit em disco |
| API | Query params em `GET /v1/templates`; `GET /v1/templates/{id}`; `TemplateListItem` alinhado ao manifest |
| CLI | `typer` sub-app `templates` com `list`, `show` e invocação sem subcomando = listagem |
| UI | `listTemplates` com query params; página de templates com filtros |
| Testes | `test_template_catalog_expansion.py` + CLI + OpenAPI |
| Docs | `TEMPLATE_CATALOG.md` + validação/handoff |

## Compatibilidade

- Respostas da API incluem campos novos; clientes antigos que ignoram campos extra continuam válidos.
- `otm templates` sem argumentos mantém o comportamento de listagem.
- `otm init -t` inalterado.

## Manutenção futura

1. Editar `registry_data.py` (ou regenerar a partir de processo interno).
2. Executar `python scripts/emit_template_catalog.py`.
3. Correr testes e validar `otm validate` / `POST instantiate` para o novo ID.
