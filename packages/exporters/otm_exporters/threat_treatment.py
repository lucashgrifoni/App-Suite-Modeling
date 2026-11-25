"""Display the treatment recorded on a declared threat in human-readable reports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import escape

from otm_core_schema import TreatmentStatus

from .export_locale import ExportArtifactLocale, normalize_export_locale
from .markdown_text import md_inline


@dataclass(frozen=True)
class TreatmentText:
    heading: str
    state: str
    rationale: str
    missing_rationale: str
    no_threats: str
    statuses: dict[TreatmentStatus, str]


_COPY: dict[ExportArtifactLocale, TreatmentText] = {
    "pt-BR": TreatmentText(
        heading="Tratamento das ameaças declaradas",
        state="Estado de tratamento",
        rationale="Justificativa",
        missing_rationale="Sem justificativa registrada.",
        no_threats="Nenhuma ameaça declarada neste modelo.",
        statuses={
            TreatmentStatus.NEW: "Nova",
            TreatmentStatus.TRIAGED: "Triada",
            TreatmentStatus.IN_PROGRESS: "Em andamento",
            TreatmentStatus.MITIGATED: "Mitigada",
            TreatmentStatus.ACCEPTED_RISK: "Risco aceito",
            TreatmentStatus.FALSE_POSITIVE: "Falso positivo",
            TreatmentStatus.WONT_FIX: "Sem correção prevista",
        },
    ),
    "en": TreatmentText(
        heading="Declared threat treatment",
        state="Treatment status",
        rationale="Rationale",
        missing_rationale="No rationale recorded.",
        no_threats="No declared threats in this model.",
        statuses={
            TreatmentStatus.NEW: "New",
            TreatmentStatus.TRIAGED: "Triaged",
            TreatmentStatus.IN_PROGRESS: "In progress",
            TreatmentStatus.MITIGATED: "Mitigated",
            TreatmentStatus.ACCEPTED_RISK: "Accepted risk",
            TreatmentStatus.FALSE_POSITIVE: "False positive",
            TreatmentStatus.WONT_FIX: "Won’t fix",
        },
    ),
}


def treatment_text(locale: str | None) -> TreatmentText:
    return _COPY[normalize_export_locale(locale)]


def markdown_literal(text: str) -> str:
    """Keep the reviewer's words visible as text, including angle brackets and Markdown punctuation."""
    return re.sub(r"([\\`*_~\[\]])", r"\\\1", escape(md_inline(text), quote=False))


def markdown_treatment_fields(status: TreatmentStatus, notes: str | None, copy: TreatmentText) -> list[str]:
    rationale = markdown_literal(notes) if notes and notes.strip() else copy.missing_rationale
    return [f"  - **{copy.state}** — {copy.statuses[status]}", f"  - **{copy.rationale}** — {rationale}"]
