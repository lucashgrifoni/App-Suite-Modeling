"""Níveis e formatos do report premium — contratos estáveis para CLI/API."""

from __future__ import annotations

from enum import StrEnum


class ReportLevel(StrEnum):
    """Profundidade do relatório entregue."""

    EXECUTIVE = "executive"
    STANDARD = "standard"
    DEEP = "deep"


class ReportFormat(StrEnum):
    """Formato de saída."""

    MARKDOWN = "markdown"
    PDF = "pdf"
