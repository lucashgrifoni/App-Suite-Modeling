from __future__ import annotations

from enum import StrEnum


class ExportFormat(StrEnum):
    document_json = "document_json"
    document_markdown = "document_markdown"
    flowchart_mermaid = "flowchart_mermaid"
    analysis_json = "analysis_json"
    analysis_markdown = "analysis_markdown"
    bundle_json = "bundle_json"
