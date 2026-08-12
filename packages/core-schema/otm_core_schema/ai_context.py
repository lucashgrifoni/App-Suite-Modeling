"""Deteção heurística de "isto é um sistema de IA" a partir do documento canônico.

Vive em `core-schema` — e não no motor — porque duas camadas precisam da **mesma** resposta:
a lente PLOT4ai (que decide se gera hipóteses) e a matriz de adequação metodologia × contexto
(que diz ao utilizador se o modelo tem contexto suficiente). Quando cada uma tinha o seu
critério, o pré-check dizia `fit: weak` ao mesmo tempo que a lente emitia nove ameaças IA
sobre o mesmo documento. Uma definição, um sítio.

Puramente lexical: sem dependências para lá do modelo canônico.
"""

from __future__ import annotations

import re

from otm_core_schema.document import ThreatModelDocument


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


def has_any(text: str, words: tuple[str, ...]) -> bool:
    return any(k in text for k in words)


_TOKEN_RE_CACHE: dict[str, re.Pattern[str]] = {}


def has_token(text: str, token: str) -> bool:
    """
    Matching pragmático por token (word-boundary simplificado).

    Evita `in` ingênuo para tokens curtos (ex.: `rag`, `llm`, `ai`) que podem aparecer como substring
    em palavras não relacionadas.

    Delimitadores considerados: qualquer coisa que não seja [a-z0-9].
    """
    tok = token.lower().strip()
    if not tok:
        return False
    rx = _TOKEN_RE_CACHE.get(tok)
    if rx is None:
        rx = re.compile(rf"(?<![a-z0-9]){re.escape(tok)}(?![a-z0-9])")
        _TOKEN_RE_CACHE[tok] = rx
    return rx.search(text) is not None


def has_any_token(text: str, tokens: tuple[str, ...]) -> bool:
    return any(has_token(text, t) for t in tokens)


_AI_COMPANION_TERMS = (
    "model",
    "agent",
    "embedding",
    "inference",
    "prompt",
    "copilot",
    "chatbot",
    "vector",
    "retrieval",
    "provider",
    "orchestrator",
    "generative",
)


def has_safe_ai_marker(text: str) -> bool:
    """
    Sinal curto `ai` só é aceite quando acompanhado de contexto técnico relacionado.

    Mantém uma heurística simples e legível para evitar colateral de substring.
    """
    if not has_any_token(text, ("ai",)):
        return False
    return has_any(text, _AI_COMPANION_TERMS)


def looks_like_ai_context(doc: ThreatModelDocument) -> bool:
    """Gate da lente PLOT4ai: evita termos genéricos (`model`, `pipeline`) que poluem não-IA."""
    tags_l = [t.lower() for t in (doc.metadata.tags or [])]
    if any(t in tags_l for t in ("ai", "llm", "rag", "genai", "generative-ai", "machine-learning", "mlops")):
        return True
    text = build_ai_calibration_corpus(doc)
    # tokens curtos: evitar substring matching ingênuo (ex.: "outrage" conter "rag")
    if has_any_token(text, ("llm", "rag")):
        return True
    if has_safe_ai_marker(text):
        return True
    return any(
        k in text
        for k in (
            "large language",
            "language model",
            "prompt",
            "embedding",
            "chatbot",
            "copilot",
            "vector db",
            "vector-db",
            "vector store",
            "vector_database",
            "tool-use",
            "tool use",
            "function calling",
            "agent orchestrat",
            "ai agent",
            "agent-api",
            "inference",
            "inferência",
            "inferencia pipeline",
            "inference pipeline",
            "fine-tune",
            "fine tune",
            "knowledge assistant",
            "retrieval service",
            "embedding service",
            "external_ai",
        )
    )
