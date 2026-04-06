"""
Locale para artefactos de exportação (Markdown, etc.).

Allowlist estrita; valores inválidos ou inesperados caem em fallback seguro (en).
Campo omitido na API → pt-BR (retrocompatível com snapshots e clientes antigos).
"""

from __future__ import annotations

from typing import Literal

ExportArtifactLocale = Literal["pt-BR", "en"]

_ALLOWED: frozenset[str] = frozenset({"pt-BR", "en"})


def normalize_export_locale(raw: str | None) -> ExportArtifactLocale:
    """
    Normaliza locale para exportação e report premium (fonte única).

    - ``None`` ou vazio → ``pt-BR`` (comportamento histórico do servidor).
    - ``pt-BR`` / ``pt-br`` / ``pt`` / tags ``pt-*`` (ex. ``pt-PT``) → ``pt-BR`` (alinhado à UI).
    - ``en`` / ``en-US`` / prefixo ``en-`` → ``en``.
    - Valor exactamente na allowlist após strip → preservado.
    - Caso contrário → ``en`` (fallback seguro; rejeita injeção / lixo).
    """
    if raw is None:
        return "pt-BR"
    s = raw.strip()
    if not s:
        return "pt-BR"
    if s in _ALLOWED:
        return s  # type: ignore[return-value]
    norm = s.replace("_", "-")
    low = norm.lower()
    if low == "pt" or low == "pt-br" or low.startswith("pt-"):
        return "pt-BR"
    if low == "en" or low.startswith("en-"):
        return "en"
    return "en"
