# Rodada de consolidação (export, audit trail, import AST opcional, E2E cockpit)

Este documento resume extensões **incrementais** alinhadas à propagação de valor semântico para fora da UI, auditabilidade do assistente e credibilidade do import de repositório.

## Audit trail do assistente (`wizard_signal_trace`)

- Modelo: `WizardSignalTraceEntry` (`packages/threat-engine/otm_threat_engine/wizard_audit_models.py`).
- Produzido no motor (`wizard_signals.apply_wizard_context_to_heuristics`, `build_corpus_mitigation_trace`) e agregado em `AnalysisResult.wizard_signal_trace`.
- Incluído no JSON de análise (ordem de chaves alinhada ao Pydantic) e em export Markdown, report premium e resumo opcional na CLI quando há notas ou traço.

## Calibração anti-overfitting (admin / API / e-commerce / ficheiros)

- Boost de ranking em perfil **admin** exige **≥2** respostas negativas nos eixos `approval`/`segregation` e **não** pode coexistir com `approval=yes` como mitigador.
- Resposta negativa **isolada** gera entrada `observation` (`wz:internal_admin_portal:isolated_no` ou `wz:api_backend_rest:isolated_no`), sem alterar scores.
- Testes: `tests/test_wizard_engine_integration.py`.

## Propagação para Markdown / premium / CLI / diff

- **Markdown da análise** (`export_analysis_markdown`): secções opcionais e curtas — contexto do assistente, audit trail, lacunas do pré-check (só checks falhados), anti-padrões.
- **Diff Markdown** (`export_comparison_markdown`): bloco **Diff semântico (resumo)** a partir de `meta.semantic_diff_sections`.
- **Report premium**: `GuidedModelingAuditBlock` + renderização após o executive summary quando há dados.
- **CLI** (`otm analyze`): após o painel principal, imprime resumo de notas e traço (limite de linhas).

## Repo import — AST leve opcional (Express)

- Variável de ambiente: `OTM_REPO_ESPRIMA=1` (ou `true`/`yes`/`on`). Requer pacote opcional `esprima` (`pip install -e ".[artifact_import_ast]"`).
- Função: `collect_express_routes_ast_lite` em `repo_ast_optional.py`; integrada em `scan_node_express_repo`.
- Cada inferência inclui `inference_source`: `regex_heuristic`, `ast_lite`, `combined` (rota vista por regex e confirmada/enriquecida por AST) ou `convention` (diretórios).
- Sem flag ou sem `esprima`: comportamento anterior (só heurística), lista AST vazia.

## E2E mínimo do cockpit

- `apps/web/e2e/cockpit.spec.ts`: mock de análise enriquecida + fluxo Home → criar modelo → Análise; valida `data-testid` do cockpit e da faixa de qualidade.

## Limitações

- AST cobre apenas padrões simples de chamadas tipo `*.get('/path')` em JS; TypeScript ou padrões dinâmicos podem falhar silenciosamente (fallback).
- O pré-check no Markdown só lista lacunas com `passed=false`; modelos “bons” não geram essa secção (evita ruído).
