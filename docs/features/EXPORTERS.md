# Exportadores (`otm_exporters`)

## Objetivo

Transformar o **modelo canónico** (`ThreatModelDocument`) e, opcionalmente, o **resultado da análise** (`AnalysisResult`) em formatos estáveis para pipelines, revisão humana e diagramas — **sem** depender de CLI, HTTP ou UI.

## Contratos e regressão

Snapshots, ordem de chaves em JSON/Markdown, erros da API relacionados e gate global: [**CONTRACT_AND_SNAPSHOTS.md**](CONTRACT_AND_SNAPSHOTS.md).

## Arquitetura

| Camada | Conteúdo |
|--------|----------|
| **Entrada** | Só tipos do core (`ThreatModelDocument`) e do motor (`AnalysisResult`). |
| **Módulos** | Um ficheiro por família: documento JSON/Markdown, análise JSON/Markdown, Mermaid, bundle JSON. |
| **Extensão** | Novos ficheiros em `otm_exporters/` + função pura; opcionalmente `protocols.py` (`DocumentTextExporter`). |
| **Diagram engine** | `otm_diagram_engine` reexporta `export_flowchart_mermaid` a partir deste pacote (uma fonte de verdade). |

## API pública

Os 17 exportadores de `otm_exporters.__all__`. `tests/test_p6_documented_exporters.py` falha se
esta lista e o pacote divergirem — esta secção listava 10 e omitia o SARIF, que é o formato de que
depende toda a integração com code scanning.

- **Documento:** `export_document_json`, `export_document_json_obj`, `export_document_markdown`
- **Análise:** `export_analysis_json`, `export_analysis_json_obj`, `export_analysis_markdown`
- **SARIF:** `export_analysis_sarif`, `export_analysis_sarif_obj` — o que a action composta publica
  em code scanning; ver [`CI_AND_SECURITY_EVIDENCE.md`](../CI_AND_SECURITY_EVIDENCE.md)
- **Backlog de remediação:** `export_remediation_backlog_json`, `export_remediation_backlog_markdown`,
  `export_remediation_backlog_obj`
- **Comparação:** `export_comparison_markdown`
- **Combinados:** `export_document_and_analysis_markdown`, `export_bundle_json`,
  `export_threat_model_bundle_json`, `export_threat_model_bundle_obj`
- **Mermaid:** `export_flowchart_mermaid`

## Dependências entre pacotes

- `otm_exporters` → `otm_core_schema` (sempre)
- `otm_exporters` → `otm_threat_engine` (exportações de análise e bundle com análise)
- `otm_exporters` → `otm_framework_mappings` (rótulos legíveis na secção Markdown de análise)

O motor **não** importa `otm_exporters` (evita ciclos).

## Exemplos de saída

Em `examples/export_samples/` (gerados a partir de `examples/minimal.otm.yaml`):

| Ficheiro | Conteúdo |
|----------|----------|
| `minimal.document.md` | Markdown só do modelo |
| `minimal.document.json` | JSON do modelo canónico |
| `minimal.analysis.json` | JSON só do resultado do motor |
| `minimal.bundle.json` | `document` + `analysis` no mesmo ficheiro |
| `minimal.flowchart.mmd` | Flowchart Mermaid (componentes e fluxos) |

Para regenerar:

```bash
python scripts/regenerate_export_samples.py
```

`tests/test_p6_export_samples_are_current.py` falha se estes ficheiros deixarem de corresponder à
saída actual. Três dos quatro tinham derivado cinco meses — o único que não derivou era o único que
já tinha um teste.
