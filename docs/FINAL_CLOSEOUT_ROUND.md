# Rodada final de fechamento (contratos, E2E, anti-patterns híbridos, diff, import, benchmark)

## Contrato TypeScript ↔ backend

- `apps/web/src/types/api.ts`: `AnalysisResult` inclui `structural_findings` e `trust_boundary_findings`; `ThreatModelComparisonResult.analysis` tipado como `AnalysisDiff | null`; `threat_delta` como `ThreatDeltaSummary`; `meta` como `ComparisonMeta` (campos estáveis + índice para extensões).
- `SessionContext`: `normalizeAnalysis` preenche listas em falta para dados antigos em `sessionStorage`.
- Testes Python: `tests/test_comparison_ts_contract_alignment.py` (chaves de `ThreatModelComparisonResult` + chaves estáveis de `meta`).

## Diff semântico (v1.2)

- `semantic_comparison.py`: `semantic_insights_version` **1.2**, `semantic_diff_sections.structural_change_summary`, `semantic_structural_refs`, `interpretation_disclaimer`.
- `threat_model_comparison.py`: `comparison_contract_version` **1.2**.
- Canais: `comparison_markdown.py`, CLI `diff` (texto com análise), UI `DiffPage` (painel semântico + bloco de refs).

## Anti-patterns híbridos

- Novos gates em `AntiPatternDefinition` (YAML): `require_any_component_kinds`, `require_min_cross_boundary_flows`, `require_component_id_contains_any`, `require_asset_name_id_contains_any`, `require_flow_flag_any`.
- `_cross_boundary_flow_ids` duplicado no módulo para evitar import circular com `engine_support`.
- Catálogo: admin (id contém `admin`), API (gateway + fluxo cross-boundary), upload (≥3 fluxos), e-commerce (id `pay`/`cart`/`shop`).
- Corpus: tags `import:signal:<texto>` em `metadata.tags` alimentam o matcher.

## Repo import

- Regex reforçada; `debug_route`; retorno com `modeling_hints` e `import_signals_corpus_snippets` para ponte ao modelador.

## Benchmark

- `benchmark_expectations_v1.json`: `min_model_completeness_score` **37** nos quatro cenários wave principais.

## E2E

- `e2e/journeys.spec.ts`: análise enriquecida, diff com meta, export com sessão; `npm run e2e:critical` agrega smoke + cockpit + journeys.

## Limitações remanescentes

- Não há paridade OpenAPI gerada automaticamente para o SPA; drift residual possível em campos opcionais não cobertos pelos testes de contrato.
- Parser de repo continua opcional e limitado a padrões Express/Node.
- Diff semântico permanece inferencial, não causal.
