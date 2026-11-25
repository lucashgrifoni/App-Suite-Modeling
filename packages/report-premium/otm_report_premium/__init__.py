"""
Report premium — agregação de dados do motor/backlog/diff e renderização MD/HTML/PDF.

A lógica de negócio permanece em `otm_threat_engine`; este pacote constrói vistas e texto.
"""

from __future__ import annotations

from .builder import build_premium_report_payload, diff_analysis_for_report
from .enums import ReportFormat, ReportLevel
from .models import PremiumReportPayload
from .pdf_export import PdfSupportUnavailable, html_to_pdf_bytes
from .render_html import render_premium_html
from .render_markdown import render_premium_markdown

__all__ = [
    "ReportLevel",
    "ReportFormat",
    "PremiumReportPayload",
    "build_premium_report_payload",
    "diff_analysis_for_report",
    "render_premium_markdown",
    "render_premium_html",
    "html_to_pdf_bytes",
    "PdfSupportUnavailable",
]
