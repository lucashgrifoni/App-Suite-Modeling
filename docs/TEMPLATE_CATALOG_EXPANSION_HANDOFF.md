# Handoff — expansão do catálogo de templates

## Resumo executivo

Foram adicionados **35 templates** novos (IDs fixos) com drafts canónicos, manifests alinhados a `TemplateInfo` estendido, emissão centralizada a partir de `registry_data.py`, filtros na API e na UI, e subcomandos CLI `templates list` / `templates show`. Mantêm-se **3 templates legados** (`saas-web`, `api-backend`, `cloud-native`) com metadados atualizados — **38 ficheiros** `*.otm.yaml` no total.

## Ficheiros principais

| Área | Ficheiros |
|------|-----------|
| Registo e dados | `otm_industry_packs/catalog/registry_data.py`, `data/templates/*.otm.yaml`, `*.meta.json` |
| Consulta partilhada | `otm_industry_packs/template_query.py` |
| Modelo | `otm_industry_packs/models.py` (`TemplateInfo`) |
| API | `otm_api/services/templates_catalog.py`, `otm_api/routers/templates.py` |
| CLI | `otm_cli/cli.py` (`templates` typer app) |
| UI | `apps/web/src/pages/TemplatesPage.tsx`, `api/otmApi.ts`, `types/api.ts` |
| Emissão | `scripts/emit_template_catalog.py` |
| Testes | `tests/test_template_catalog_expansion.py`, `tests/test_cli.py`, `tests/test_api.py` |
| Docs | `docs/TEMPLATE_CATALOG.md`, `docs/TEMPLATE_CATALOG_EXPANSION_*.md` |

## Fluxos suportados

- **UI:** listagem com filtros; aplicar template → assistente.
- **API:** listar, filtrar, detalhe, instanciar.
- **CLI:** `otm templates`, `otm templates list`, `otm templates show`, `otm init -t`.

## Próxima rodada sugerida

1. Internacionalização dos rótulos de categoria na UI (hoje chaves estáveis + `category_label` do manifest).
2. Testes E2E leves na página Templates (filtro + usar template) se a suite Playwright ainda não cobrir.
3. Avaliar compressão de `registry_data.py` (arquétipos) se o catálogo duplicar padrões.

## Decisão final

**READY** — conforme `TEMPLATE_CATALOG_EXPANSION_VALIDATION.md`.
