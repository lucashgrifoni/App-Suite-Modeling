# Fase de inovação — Frente 1: Diff entre versões do threat model

## Objetivo

Permitir comparar **duas versões válidas** do mesmo artefato canónico (`ThreatModelDocument`) para revisão de PRs, auditoria de mudanças e governança de modelos-as-code, **sem** alterar o schema nem o contrato existente dos outros endpoints.

## Arquitetura incremental

| Camada | Implementação | Notas |
|--------|---------------|--------|
| **Domínio** | `otm_core_schema.diff.diff_documents` | Única fonte de verdade da semântica de comparação. |
| **CLI** | `otm diff BASELINE REVISED` | Orquestra I/O; chama o core. |
| **API** | `POST /v1/models/diff` | Valida `baseline` e `revised` como documentos completos; delega ao core. |
| **UI** | `/diff` | Baseline = sessão; revisão = JSON colado/carregado; chama a API. |

Nenhuma lógica de negócio duplicada no front: apenas serialização e chamada HTTP.

## Contratos impactados

- **Novo** módulo e tipos no `packages/core-schema`: `ThreatModelDiff`, `diff_documents`, etc.
- **Novo** corpo `DiffBody` em `otm_api.schemas.bodies` (`baseline`, `revised`).
- **Novo** endpoint OpenAPI: `POST /v1/models/diff`.
- **Compatibilidade**: endpoints e schema canónico **inalterados**; adição puramente extensiva.

## Semântica do diff (v1)

- Secções com listas indexadas por `id` (`components`, `data_flows`, `threats`, …): `added`, `removed`, `modified` com alterações **por campo** no `model_dump(mode="json")` de cada entidade (objetos aninhados comparados como um campo único se diferirem).
- `model_info`, `metadata`, `business_context`, `residual_risk_summary`: lista de `FieldChange`.
- Opcionais ausentes num dos lados: `FieldChange` com `field="*"` indica bloco adicionado/removido.

## Limitações atuais (v1)

- Não há diff de **YAML** preservando comentários (entradas são documentos já parseados).
- Não há merge automático nem resolução de conflitos.
- Ordem de listas sem `id` não é comparada (no canónico, listas relevantes são sempre por `id`).
- Métricas agregadas no `summary_line` são heurísticas de contagem; o detalhe está nas secções.

## Evolução (compare + análise)

A frente foi estendida com **`ThreatModelComparisonResult`**, CLI `--with-analysis` / `diff-analysis`, endpoints `POST /v1/models/compare` e `POST /v1/analyses/diff`, e export Markdown. Documentação consolidada: **`docs/THREAT_MODEL_DIFF.md`**.

## Validação

- Testes: `tests/test_document_diff.py`, `tests/test_threat_model_comparison.py`, `tests/test_api.py`, `tests/test_cli.py`.
- Smoke manual: `otm diff examples/minimal.otm.yaml examples/minimal.otm.yaml`.
