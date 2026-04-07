# Contratos de saída, erros da API e snapshots

Documento operacional para **Fase A** do plano de qualidade: saber o que é contrato estável, onde está testado e como atualizar snapshots.

## 1) Matriz artefacto → teste → validação

| Artefacto / contrato | Onde está testado | Comando típico |
|----------------------|-------------------|----------------|
| JSON do documento (`export_document_json`) — snapshot, ordens (componente com `technology`, SaaS, etc.) | `tests/test_exporters.py` (`test_export_document_json_minimal_nested_entity_key_order_stable` inclui API com `technology`, …) | `python -m pytest tests/test_exporters.py -k document_json -v` |
| `export_bundle_json` — ordem serializada | `tests/test_exporters.py` (`test_export_bundle_json_string_top_level_key_order_stable`) | `python -m pytest tests/test_exporters.py -k bundle_json_string_top -v` |
| Markdown do documento — snapshot + ordem de secções (`minimal` e exemplo completo) | `tests/test_exporters.py` (snapshot minimal, `test_export_document_markdown_minimal_heading_order_stable`, `test_export_document_markdown_full_example_heading_order_stable`) | `python -m pytest tests/test_exporters.py -k document_markdown -v` |
| JSON da análise (`export_analysis_json`) — topo, `summary`, avisos estruturais, heurística, `FrameworkRef`, fronteira, `methodology_insights` | `tests/test_exporters.py` (incl. `test_export_analysis_json_structural_finding_key_order_stable`, `test_export_analysis_json_minimal_framework_ref_key_order_stable`, …) | `python -m pytest tests/test_exporters.py -k analysis_json -v` |
| Markdown da análise (modo harmonizado) — snapshot + ordem de secções `###` | `tests/test_exporters.py` (`test_export_analysis_markdown_snapshot_minimal_harmonized`, `test_export_analysis_markdown_harmonized_minimal_h3_heading_order_stable`) | `python -m pytest tests/test_exporters.py -k analysis_markdown -v` |
| Bundle documento + análise — ordem `document`, `analysis` | `tests/test_exporters.py` (`test_export_threat_model_bundle_obj_top_level_key_order_stable`) | `python -m pytest tests/test_exporters.py -k bundle_obj_top_level -v` |
| Mermaid flowchart — estrutura (nós vs arestas) | `tests/test_exporters.py` (`test_export_flowchart_mermaid_minimal_node_and_edge_line_counts`) | `python -m pytest tests/test_exporters.py -k flowchart_mermaid_minimal_node -v` |
| Chaves raiz `AnalysisResult` em JSON + paridade `json`/`obj` | `tests/test_exporters.py` (`test_export_analysis_json_and_markdown`, `test_export_threat_model_bundle_obj_matches_parsed_bundle_json`) | `python -m pytest tests/test_exporters.py -v` |
| Bundle (`document` + `analysis`) | `tests/test_exporters.py`, `tests/test_api.py` (`test_export_bundle_runs_analysis`) | `python -m pytest tests/test_exporters.py tests/test_api.py -k bundle -v` |
| Resposta `POST /v1/models/analyze` (chaves estáveis) | `tests/test_api.py` (`test_analyze_contract_keys_stable`) | `python -m pytest tests/test_api.py -k contract_keys -v` |
| Erros API (`detail.code` + forma) | `tests/test_api.py` (`test_validate_invalid_document`, `test_*_pack_*`, `test_export_invalid_analysis_*`, `test_instantiate_unknown_template`) | `python -m pytest tests/test_api.py -k "invalid\|unknown\|detail" -v` |
| Códigos `StructuralFinding` por lente | `tests/test_methodology_lenses_structural_contracts.py` | `python -m pytest tests/test_methodology_lenses_structural_contracts.py -v` |
| CLI — comandos críticos | `tests/test_cli.py` | `python -m pytest tests/test_cli.py -v` |
| Fronteira core sem imports de adaptador | `tests/test_core_adapter_boundary.py`, CI | `python scripts/check_core_adapter_boundary.py` |

Códigos de erro HTTP estáveis:

**Rotas (corpo em `detail`):** implementação em `apps/api/otm_api/routers/_errors.py`.

- `DOCUMENT_VALIDATION_ERROR` (422)
- `ANALYSIS_VALIDATION_ERROR` (422)
- `TEMPLATE_INVALID` (422)
- `PACK_NOT_FOUND` (404)
- `TEMPLATE_NOT_FOUND` (404)

**Validação de envelope FastAPI** (corpo JSON **sem** chave `detail`): handler em `apps/api/otm_api/errors.py`.

- `REQUEST_VALIDATION_ERROR` (422) — resposta plana com `code`, `message`, `status`, `errors`.

Ver `tests/test_api.py` (`test_validate_missing_body_field_uses_request_validation_handler`).

## 2) Quando usar snapshot

**Usar snapshot** quando o output for **determinístico** para uma entrada fixa (ex.: [`examples/minimal.otm.yaml`](../../examples/minimal.otm.yaml)) e quiseres **detectar qualquer diferença** de texto (JSON/Markdown).

**Não usar snapshot completo** para:

- `analysis_json` / análise inteira ligada a evolução frequente do motor (preferir **subconjunto de chaves** ou invariantes, como já em `test_export_analysis_json_and_markdown` e `test_analyze_contract_keys_stable`).
- Dados dependentes de ordem não garantida entre versões Pydantic/Python sem `sort_keys` explícito (rever após upgrades maiores).

## 3) Como atualizar snapshots

O projeto **não** usa ferramenta de “approve snapshot” automática: os ficheiros em `tests/snapshots/` são a **fonte esperada** literal.

1. Falhou um teste de snapshot? Reproduzir: `python -m pytest tests/test_exporters.py -k snapshot -v`.
2. Inspecionar o diff: confirmar se a mudança é **intencional** (nova secção, correção de bug, mudança de copy).
3. Se for intencional, **substituir** o ficheiro em `tests/snapshots/` pelo novo output (ou copiar o output gerado para o snapshot após revisão em PR).
4. Para o snapshot de análise Markdown harmonizado, garantir `OTM_MARKDOWN_VIEW_MODE=harmonized` (o teste já define no `os.environ`).

## 4) Gate global

Antes de RC ou merges grandes:

```bash
python scripts/run_global_regression_gate.py
```

O gate inclui `scripts/check_core_adapter_boundary.py` como primeiro passo. Ver também [RELEASE_CHECKLIST_RC.md](../internal/checklists/RELEASE_CHECKLIST_RC.md).

## 5) Fronteira core vs adaptadores

O script `scripts/check_core_adapter_boundary.py` falha se `packages/core-schema` ou `packages/threat-engine` importarem módulos de framework de entrega (`fastapi`, `typer`, etc.). Corre no CI após o Ruff.
