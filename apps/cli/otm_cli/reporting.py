"""Relatório Markdown da CLI — delega a `otm_exporters` (sem lógica duplicada)."""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument
from otm_exporters.analysis_markdown import (
    export_analysis_markdown,
    export_document_and_analysis_markdown,
)
from otm_threat_engine import AnalysisResult


def export_analysis_section_markdown(result: AnalysisResult) -> str:
    """Secção Markdown com análise heurística (alias estável para a CLI)."""
    return export_analysis_markdown(result)


def export_full_report_markdown(doc: ThreatModelDocument, result: AnalysisResult) -> str:
    """Documento canónico + resultado do motor."""
    return export_document_and_analysis_markdown(doc, result)
