"""Texto agregado do documento para deteção heurística de contexto IA (calibração + PLOT4ai)."""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument


def _entity_corpus_parts(doc: ThreatModelDocument) -> list[str]:
    """Tokens de componentes, fluxos, fronteiras e ativos (com defaults vazios)."""
    parts: list[str] = []
    for c in doc.components:
        parts.extend([c.id, c.name, (c.description or ""), (c.technology or "")])
    for f in doc.data_flows:
        parts.extend([f.id, f.name or "", (f.description or ""), (f.protocol or "")])
    for tb in doc.trust_boundaries:
        parts.extend([tb.id, tb.name, (tb.description or "")])
    for a in doc.assets:
        parts.extend([a.id, a.name, (a.description or ""), str(a.sensitivity or "")])
    return parts


def build_ai_calibration_corpus(doc: ThreatModelDocument) -> str:
    """
    Corpus lexical estável para keywords — inclui nomes/descrições de componentes, fluxos,
    fronteiras e ativos (alinhado com fixtures realistas OTM v1).
    """
    parts: list[str] = [
        doc.metadata.title or "",
        doc.metadata.summary or "",
        " ".join(doc.metadata.tags or []),
        (doc.business_context.description if doc.business_context else "") or "",
        (doc.business_context.regulatory_context if doc.business_context else "") or "",
    ]
    parts.extend(_entity_corpus_parts(doc))
    if doc.import_signals_corpus:
        parts.append(doc.import_signals_corpus)
    return " ".join(parts).lower()
