# Rodada avançada — UI adaptativa, benchmark, diff semântico, import repo, anti-patterns

## Wizard → motor (pipeline)

1. O assistente grava respostas em `metadata.tags` no formato `wz:<template_semantic_profile>:<id>=yes|no|unk`.
2. `wizard_signals.py` interpreta tags **no motor** (não no browser).
3. **Anti-patterns**: respostas `yes` a controlos esperados geram *keywords sintéticas* no corpus (reduz falsos positivos de `missing_any_of`).
4. **Ranking**: sinais negativos declarados (ex.: sem aprovação em admin) aplicam reforço conservador de impacto (+1) em heurísticas cuja família coincide, com `signal_refs` contendo `wizard:context_boost`.
5. `AnalysisResult.wizard_context_notes` descreve a influência para relatórios e UI.

## Benchmark oficial ampliado

- Expectativas versionadas: `tests/fixtures/golden/benchmark_expectations_v1.json`
- Testes: `tests/test_official_benchmark.py` (templates wave, PASTA, NIST parcial, métricas `compute_benchmark_metrics`)

## Diff semântico

- Motor: `semantic_comparison.enrich_comparison_meta` → `meta.semantic_insights`, `meta.semantic_diff_sections` (melhorou / piorou / impacto de risco), versão `1.1`
- UI: página **Diff** mostra secções e lista de insights quando a API as envia

## Import repo-level

- CLI: `otm import repo <dir> [--json-out FILE]`
- Biblioteca: `otm_artifact_import.scan_node_express_repo` — rotas, `app.use` mounts, multer, sessão, fetch, eval/exec, auth/JWT/passport, `/admin`, `child_process`, pastas `public/uploads/static/dist`

## Anti-pattern library

- Catálogo: `packages/threat-engine/otm_threat_engine/data/anti_patterns/catalog.yaml`
- Resultado de análise: campo `anti_pattern_hits` em `AnalysisResult`

## UI adaptativa

- Constantes: `apps/web/src/constants/adaptiveWizard.ts` (perguntas por `template_semantic_profile`, tags `wz:...`)
- Assistente: passo **Contexto** com metodologia alvo, perfil opcional e perguntas adaptativas
- Qualidade: `ModelQualityStrip` na página **Análise** (precheck, completude metodológica, anti-patterns em disclosure)
- Revisão: edição de trust boundaries (nota, validação) e ativos (criticidade, classificação) em **Diagrama lógico**
