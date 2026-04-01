"""Compatibilidade: diagramas Mermaid vivem em `otm_exporters` (fonte única)."""

from __future__ import annotations

from otm_exporters.mermaid_flowchart import export_flowchart_mermaid

__all__ = ["export_flowchart_mermaid"]
