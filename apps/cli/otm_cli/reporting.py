"""CLI Markdown report — delegates to `otm_exporters` (no duplicated logic)."""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument
from otm_exporters.analysis_markdown import (
    export_analysis_markdown,
    export_document_and_analysis_markdown,
)
from otm_threat_engine import AnalysisResult


def export_analysis_section_markdown(result: AnalysisResult) -> str:
    """Markdown section with heuristic analysis (stable alias for the CLI)."""
    return export_analysis_markdown(result)


def export_full_report_markdown(doc: ThreatModelDocument, result: AnalysisResult) -> str:
    """Canonical document + engine result."""
    return export_document_and_analysis_markdown(doc, result)
