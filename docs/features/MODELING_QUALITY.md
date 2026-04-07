# Qualidade de modelagem e análise (schema 1.1+)

Este documento resume campos e mecanismos usados para **contexto rico**, **completude de metodologia**, **pré-check de modelo** e **anti-leakage de recomendações**, sem substituir auditoria humana.

## Ativos (`Asset`)

| Campo | Descrição |
| --- | --- |
| `id`, `name`, `asset_kind` | Identidade e tipo (`credential`, `pii`, `order_record`, `session`, `uploaded_content`, `admin_capability`, `audit_log`, `configuration_secret`, …). |
| `sensitivity` / `data_classification` | Texto legado ou enum `DataClassificationLevel` (`public` … `restricted`). |
| `data_nature` | Natureza dos dados (credenciais, sessões, perfis, pedidos, logs, ficheiros carregados). |
| `business_criticality`, `regulatory_relevance`, `owner`, `location` | Impacto e governação. |
| `related_component_ids`, `related_data_flow_ids` | Ligações obrigatórias para validação cruzada. |

Componentes podem referenciar ativos via `asset_ids`. **Datastores relevantes** devem estar ligados a pelo menos um ativo em modelos bem preenchidos.

## Fronteiras de confiança (`TrustBoundary`)

Além de `member_component_ids`, o modelo suporta `outside_component_ids`, `crossing_flow_ids`, `boundary_scenario` (ex.: `boundary_client_to_server`), e notas de inferência vs validação manual quando aplicável.

## Fluxos (`DataFlow`)

Semântica de fluxo: `protocol`, `data_types`, `semantic_class` (`FlowSemanticClass`), `public_exposure`, `auth_required`, `stores_sensitive_data`, `supports_file_upload`, flags de fetch externo e redirecionamento, alinhados ao motor de heurísticas compostas.

## Componentes (`Component`)

Metadados de exposição e função: `exposure_type`, `responsibility`, `privilege_level`, `handles_credentials`, `handles_sensitive_data`, `executes_code_or_commands`, `serves_user_content`, `has_direct_datastore_access`, `supports_admin_operations`, `supports_debug_features`, `technology_role`, associação a fronteira.

## Completude de metodologia

`MethodologyCompletenessState`: `complete`, `partial`, `degraded`. PASTA sem objetivos/ativos suficientes ou NIST DC sem classificação de dados tende a `partial`/`degraded`; o relatório deve refletir o estado.

## Pré-check de qualidade (`ModelQualityPrecheck`)

O motor pode anexar `model_quality_precheck` ao `AnalysisResult` com:

- `score_0_100` (0–100)
- `band`: **minimal** | **good** | **rich** (agregado do score)
- `methodology_fit` (`strong` / `partial` / `weak`) para a metodologia principal do documento
- `recommendation_confidence` (`low` / `medium` / `high`)
- `methodology_fit_matrix`: mapa por metodologia (`stride`, `pasta`, …)
- `checks[]`: itens com `code`, `passed`, `message` (ativos, fronteiras, semântica de fluxos, componentes, negócio, classificação)

Interpretação rápida: **minimal** = modelo ainda fraco para análise contextual; **good** / **rich** = mais sinais para o motor e para NIST/PASTA. Testes dedicados: `tests/test_model_quality_precheck.py` (cenários minimal / bom via `examples/minimal.otm.yaml` / rico construído em YAML).

## Recomendações e anti-leakage

Sugestões de controlo dos industry packs passam por `filter_pack_control_hints` (`recommendation_gate.py`): pagamento, admin, upload, e **entitlement / subscription / premium / benefício comercial** só passam se existirem âncoras no modelo (texto, ativos ou mesma linha que pagamento). Testes: `tests/test_recommendation_gate.py` (incl. `test_entitlement_subscription_and_premium_hints_suppressed_without_commercial_signals`).

## NIST Data-Centric — completude

Sem ativos: estado **degraded**. Com ativos mas sem `data_classification` (nem sensibilidade reconhecível): **partial**. Testes: `tests/test_methodology_completeness_nist.py`.

## Templates industry

Os ficheiros em `packages/industry-packs/otm_industry_packs/data/templates/` incluem **pelo menos três ativos** plausíveis por defeito, com ligações a componentes e fluxos. Para regenerar ou ajustar em lote, ver `scripts/fill_industry_template_assets.py`.

## Matriz de adequação metodológica

`build_methodology_fit_matrix(doc)` devolve, por metodologia (`stride`, `pasta`, `nist_data_centric`, `linddun`, `plot4ai`), um de: **strong** | **partial** | **weak**. O mesmo mapa está em `ModelQualityPrecheck.methodology_fit_matrix` (pré-check).

## API e CLI — pré-check

- **HTTP:** `POST /v1/models/precheck` com corpo `{ "document": { … } }` e opcional `methodology`. Resposta: `precheck` + `methodology_completeness`.
- **CLI:** `otm precheck modelo.otm.yaml` ou `otm precheck modelo.otm.yaml --json-out precheck.json`

## Benchmark (onda 2)

A suíte `tests/test_modeling_benchmark_wave2.py` valida templates-chave (`industry-ecommerce`, `admin-portal`, `file-upload-processing`, `api-public`): ativos, fronteiras (incl. DMZ no upload), score de pré-check, presença de `methodology_fit_matrix`, PASTA degradado em `api-public` sem objetivos, e ausência de hints de pagamento do pack finance no `admin-portal` sem âncora de pagamento.
