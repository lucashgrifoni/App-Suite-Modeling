# Diff semântico de threat models

Comparar **duas versões** do documento canónico (`ThreatModelDocument`) e, opcionalmente, **dois resultados de análise** (`AnalysisResult`), para revisão de PRs, change management e pipelines DevSecOps — sem depender de diff textual de YAML.

## Quando usar

| Cenário | Abordagem |
|--------|-----------|
| Só estrutura (componentes, fluxos, boundaries, ameaças canónicas no YAML) | `otm diff` ou `POST /v1/models/diff` |
| Estrutura + agregados + insights + opcional motor | `otm diff --with-analysis` ou `POST /v1/models/compare` |
| Já tem dois JSON de análise (ex.: CI guardou artefactos) | `otm diff-analysis` ou `POST /v1/analyses/diff` |
| Relatório legível para humanos | `otm diff --format markdown` (usa `otm_exporters.comparison_markdown`) |

## Arquitetura (separação de responsabilidades)

| Camada | Módulo | Conteúdo |
|--------|--------|----------|
| **Diff estrutural** | `otm_core_schema.diff` | `diff_documents` → `ThreatModelDiff` (por `id`, alterações por campo) |
| **Insights estruturais** | `otm_core_schema.diff_insights` | Frases explicativas a partir do diff (sem motor) |
| **Diff de análise** | `otm_threat_engine.analysis_diff` | `diff_analysis_results` → `AnalysisDiff` |
| **Deltas agregados** | `otm_threat_engine.comparison_models` | `RiskDeltaSummary`, `ThreatDeltaSummary`, `RecommendationDelta`, etc. |
| **Orquestração** | `otm_threat_engine.threat_model_comparison` ag `compare_threat_models` | Junta estrutura + análise opcional |
| **Export** | `otm_exporters.comparison_markdown` | Relatório Markdown executivo |
| **API** | `otm_api.routers.models`, `otm_api.routers.analyses` | HTTP + validação Pydantic |
| **CLI** | `otm_cli.cli` | `diff`, `diff-analysis` |

O contrato **`POST /v1/models/diff`** mantém-se: resposta = `ThreatModelDiff` apenas. **`POST /v1/models/compare`** devolve `ThreatModelComparisonResult` (superset).

## Matching entre versões

- **Documento**: entidades em listas com `id` — comparação **por `id`**; adicionados/removidos/modificados são estáveis.
- **Heurísticas do motor** (em `AnalysisDiff`): matching principal por **`threat_id`**; **assinatura semântica** (metadados como STRIDE + alvos + prefixo do título) gera apenas **`signature_remap_hints`** e sugestões de remapeamento — **não** funde entidades automaticamente (comportamento previsível).

## Contrato de saída (`ThreatModelComparisonResult`)

Campos úteis para CLI, API, UI e export:

- `summary` — headline e flags (`has_structural_changes`, `has_analysis_changes`, …)
- `aggregate` — listas `added` / `removed` / `changed` por secção (IDs)
- `structural` — mesmo formato que `/v1/models/diff`
- `structural_insights`, `analysis_insights`, `key_insights` — texto acionável
- `risk_delta`, `threat_delta`, `recommendation_delta` — deltas focados
- `meta` — extensível (ex.: versão do contrato de diff)

## Como interpretar

- **Ameaças canónicas** (campo `threats` no documento) aparecem no diff estrutural e em `aggregate.threats`.
- **Ameaças heurísticas** do motor aparecem em `analysis.heuristic_threats` quando há análise.
- **Risco**: `risk_delta.analysis_max_score_delta` reflete variação do score máximo entre execuções; listas `heuristic_increased_ids` / `heuristic_decreased_ids` detalham movimento por ID.
- Mensagens do tipo *“Novo fluxo externo cruzou trust boundary”* surgem em `key_insights` / `structural_insights` quando os dados o suportam.

## Exemplos CLI

```bash
# Só estrutura, JSON
otm diff baseline.otm.yaml revised.otm.yaml

# Com motor nos dois lados + Markdown
otm diff baseline.otm.yaml revised.otm.yaml --with-analysis --format markdown

# Resumo curto
otm diff baseline.otm.yaml revised.otm.yaml --summary-only

# Dois ficheiros de análise
otm diff-analysis old-analysis.json new-analysis.json
```

## Exemplos API

Ver `docs/API.md` — `POST /v1/models/compare`, `POST /v1/analyses/diff`.

Corpo mínimo de compare:

```json
{
  "baseline": { "model": {}, "metadata": {} },
  "revised": { "model": {}, "metadata": {} },
  "run_analysis": false
}
```

Regra: **`baseline_analysis` e `revised_analysis` devem vir os dois ou nenhum**. Com `run_analysis: true`, o servidor corre o motor em ambos se não forem enviadas análises.

## Limitações atuais

- Sem diff de ficheiro YAML cru (comentários / formatação).
- Sem merge automático de modelos.
- Assinatura heurística não substitui IDs para mutação de dados — só orienta interpretação.
- Modelos muito grandes: considere `--summary-only` ou consumir só `aggregate` + `key_insights`.

## Testes relacionados

- `tests/test_document_diff.py`, `tests/test_threat_model_comparison.py`, `tests/test_api.py`, `tests/test_cli.py`

## Ver também

- `docs/INNOVATION_PHASE_1_THREAT_MODEL_DIFF.md` — histórico da frente inicial (diff estrutural v1)
