"""
Locale para artefactos de exportação (Markdown, etc.).

Allowlist estrita; valores inválidos ou inesperados caem em fallback seguro (en).
Campo omitido na API → pt-BR (retrocompatível com snapshots e clientes antigos).
"""

from __future__ import annotations

from typing import Literal

ExportArtifactLocale = Literal["pt-BR", "en"]

_ALLOWED: frozenset[str] = frozenset({"pt-BR", "en"})


def recognized_export_locale(raw: str | None) -> ExportArtifactLocale | None:
    """A língua que esta tag nomeia, ou ``None`` quando não nomeia nenhuma das suportadas.

    Separado de `normalize_export_locale` porque as duas fronteiras precisam de respostas
    diferentes para o mesmo lixo. Um servidor não pode rebentar por causa de um campo opcional
    mal preenchido, por isso normaliza e continua. Uma linha de comandos pode — e deve: quem
    escreve `--locale ptBR` (a gralha óbvia de `pt-BR`) recebia um relatório **em inglês**, exit
    0, sem aviso — uma língua diferente da que teria recebido sem a flag nenhuma. Aqui devolve-se
    "não reconheço" para que o CLI recuse como recusa qualquer outro enum.
    """
    if raw is None:
        return "pt-BR"
    s = raw.strip()
    if not s:
        return "pt-BR"
    if s in _ALLOWED:
        return s  # type: ignore[return-value]
    low = s.replace("_", "-").lower()
    if low == "pt" or low.startswith("pt-"):
        return "pt-BR"
    if low == "en" or low.startswith("en-"):
        return "en"
    return None


def normalize_export_locale(raw: str | None) -> ExportArtifactLocale:
    """
    Normaliza locale para exportação e report premium (fonte única).

    - ``None`` ou vazio → ``pt-BR`` (comportamento histórico do servidor).
    - ``pt-BR`` / ``pt-br`` / ``pt`` / tags ``pt-*`` (ex. ``pt-PT``) → ``pt-BR`` (alinhado à UI).
    - ``en`` / ``en-US`` / prefixo ``en-`` → ``en``.
    - Valor exactamente na allowlist após strip → preservado.
    - Caso contrário → ``en`` (fallback seguro; rejeita injeção / lixo).
    """
    return recognized_export_locale(raw) or "en"
