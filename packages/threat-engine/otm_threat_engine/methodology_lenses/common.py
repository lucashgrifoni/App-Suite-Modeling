from __future__ import annotations

import re

from otm_core_schema import RiskAssessment, StrideCategory, ThreatModelDocument, ThreatModelMethodology

from otm_threat_engine.ai_modeling.corpus import build_ai_calibration_corpus
from otm_threat_engine.result import (
    AnalysisResult,
    HeuristicThreat,
    MethodologyInsightBlock,
    MethodologyInsights,
    StructuralFinding,
)


def append_engine_lens_note(
    result: AnalysisResult,
    *,
    methodology: ThreatModelMethodology,
    note: str,
) -> AnalysisResult:
    findings = [
        *result.structural_findings,
        StructuralFinding(
            code=f"ENGINE_LENS_{methodology.value.upper()}",
            severity="info",
            message=note,
        ),
    ]
    return result.model_copy(update={"structural_findings": findings})


def append_methodology_insights(
    result: AnalysisResult,
    *,
    profile: str,
    blocks: list[tuple[str, str, list[str]]],
) -> AnalysisResult:
    insight_blocks = [MethodologyInsightBlock(key=key, title=title, items=items) for key, title, items in blocks]
    insights = MethodologyInsights(profile=profile, blocks=insight_blocks)
    return result.model_copy(update={"methodology_insights": insights})


def boost_impact(result: AnalysisResult, predicate) -> AnalysisResult:
    boosted = []
    for h in result.heuristic_threats:
        if predicate(h):
            new_impact = min(5, h.risk.impact + 1)
            risk = h.risk.model_copy(
                update={
                    "impact": new_impact,
                    "score": float(h.risk.likelihood * new_impact),
                }
            )
            boosted.append(h.model_copy(update={"risk": risk}))
        else:
            boosted.append(h)
    return result.model_copy(update={"heuristic_threats": boosted})


def append_heuristics_from_entries(
    out: list[HeuristicThreat],
    existing: set[str],
    entries: list[tuple[str, str, str, StrideCategory, int, int]],
    *,
    target_component_id: str | None = None,
    target_data_flow_id: str | None = None,
) -> None:
    for hid, title, desc, stride, likelihood, impact in entries:
        if hid in existing:
            continue
        out.append(
            HeuristicThreat(
                id=hid,
                title=title,
                description=desc,
                stride=stride,
                target_component_id=target_component_id,
                target_data_flow_id=target_data_flow_id,
                risk=RiskAssessment(
                    likelihood=likelihood,
                    impact=impact,
                    score=float(likelihood * impact),
                ),
                skipped_as_duplicate=False,
            )
        )
        existing.add(hid)


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
