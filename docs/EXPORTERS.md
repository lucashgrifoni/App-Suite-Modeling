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

## API pública (MVP)

- **Documento:** `export_document_json`, `export_document_json_obj`, `export_document_markdown`
- **Análise:** `export_analysis_json`, `export_analysis_json_obj`, `export_analysis_markdown`
- **Combinados:** `export_document_and_analysis_markdown`, `export_bundle_json`, `export_threat_model_bundle_json`
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

Para regenerar: `python -c "..."` (ver comentário no repositório ou script de manutenção futuro).
