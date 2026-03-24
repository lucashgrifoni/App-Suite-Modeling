"""
Exportadores de texto: JSON, Markdown e Mermaid.

**Convenções**
- Entradas: `ThreatModelDocument` validado e/ou `AnalysisResult` do motor.
- Sem dependência de Typer, Rich ou HTTP — apenas `otm_core_schema`,
  `otm_threat_engine` (para análise) e `otm_framework_mappings` (notas de framework na MD de análise).

Novos formatos: novos módulos (`otm_exporters/<formato>.py`) e registo em `__all__`.
"""

from otm_exporters.analysis_json import export_analysis_json, export_analysis_json_obj
from otm_exporters.analysis_markdown import (
    export_analysis_markdown,
    export_document_and_analysis_markdown,
)
from otm_exporters.bundle_json import export_bundle_json, export_threat_model_bundle_json
from otm_exporters.document_json import export_document_json, export_document_json_obj
from otm_exporters.document_markdown import export_document_markdown
from otm_exporters.mermaid_flowchart import export_flowchart_mermaid
from otm_exporters.protocols import DocumentTextExporter, DocumentTextExporterWithOptions

__all__ = [
    "export_analysis_json",
    "export_analysis_json_obj",
    "export_analysis_markdown",
    "export_bundle_json",
    "export_document_and_analysis_markdown",
    "export_document_json",
    "export_document_json_obj",
    "export_document_markdown",
    "export_flowchart_mermaid",
    "export_threat_model_bundle_json",
    # Extensibilidade
    "DocumentTextExporter",
    "DocumentTextExporterWithOptions",
]
