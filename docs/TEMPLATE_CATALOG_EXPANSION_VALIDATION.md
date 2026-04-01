# Validação — expansão do catálogo de templates

## Critérios de sucesso

| Critério | Evidência |
|----------|-----------|
| 35 IDs da expansão presentes | `tests/test_template_catalog_expansion.py::test_expansion_template_ids_registered` |
| YAML válido contra schema canónico | `test_each_template_yaml_loads_document` |
| Manifest com categoria e título | `test_each_template_has_manifest_with_category` |
| Filtros API/CLI | `test_api_templates_list_filter`, `test_templates_list_filter` |
| Detalhe API | `test_api_template_detail`, `test_api_template_detail_404` |
| Instantiate por template | `test_instantiate_all_templates` |
| Coerência IA / sensível | `test_filter_plot4ai_templates_have_hint`, `test_sensitive_objective_template_uses_linddun` |
| Regressão global | `pytest tests/` (284 testes na última execução local) |
| Build frontend | `npm run build` em `apps/web` |

## Suíte executada

- `python -m pytest tests/` — ver relatório local na última execução.
- Smoke E2E do projeto (se configurado no CI) deve permanecer verde; não altera rotas críticas além de `/v1/templates`.

## Limitações atuais

- Catálogo embutido em pacote; não há templates dinâmicos por tenant.
- Filtro de tag na API é correspondência exata (case-insensitive), não substring.

## Decisão

**READY** para integração incremental, assumindo CI e revisão humana do conteúdo dos YAMLs.
