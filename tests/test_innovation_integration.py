"""Integração final das 5 frentes de inovação sem regressão de contrato."""

from __future__ import annotations

from pathlib import Path

from otm_artifact_import import import_openapi_text
from otm_core_schema import Metadata, load_document_from_yaml_path
from otm_core_schema.enums import ThreatModelMethodology
from otm_exporters.analysis_markdown import export_analysis_markdown
from otm_threat_engine import analyze_document, build_remediation_backlog, compare_threat_models

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"

_OPENAPI_AI = """
openapi: 3.0.0
info:
  title: LLM Gateway API
  version: 1.0.0
servers:
  - url: https://api.example.com
paths:
  /chat:
    post:
      operationId: chatCompletion
"""


def test_integration_fronts_plot4ai_explainability_backlog_diff_import() -> None:
    imported = import_openapi_text(_OPENAPI_AI, filename="openapi.yaml")
    assert imported.inferences
    assert imported.explanations

    base_doc = load_document_from_yaml_path(_MINIMAL)
    doc = imported.document.model_copy(
        update={
            "metadata": Metadata(
                title="LLM RAG agent app",
                summary="Retrieval embeddings vector store e tool use externo",
            )
        }
    )
    analysis = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    assert analysis.explanations
    assert analysis.ai_system_context is not None
    assert analysis.methodology_insights is not None

    backlog = build_remediation_backlog(analysis, doc)
    assert backlog.items
    assert backlog.items[0].explanations

    compare = compare_threat_models(base_doc, doc, baseline_analysis=analyze_document(base_doc), revised_analysis=analysis)
    assert compare.explanations

    md = export_analysis_markdown(analysis)
    assert "Explicabilidade" in md
    assert "PLOT4ai" in md
