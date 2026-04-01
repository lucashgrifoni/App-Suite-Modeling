"""
Modelagem incremental de sistemas AI/LLM — sinais do documento, heurísticas PLOT4ai e síntese.

Mantém-se desacoplado do núcleo STRIDE: a lente `plot4ai` orquestra estes módulos.
"""

from otm_threat_engine.ai_modeling.explanations import append_plot4ai_merge_explanations
from otm_threat_engine.ai_modeling.heuristics import extra_plot4ai_heuristic_entries
from otm_threat_engine.ai_modeling.signals import AiSignalBundle, collect_ai_signals_from_document
from otm_threat_engine.ai_modeling.summary import build_ai_system_context_summary

__all__ = [
    "AiSignalBundle",
    "append_plot4ai_merge_explanations",
    "build_ai_system_context_summary",
    "collect_ai_signals_from_document",
    "extra_plot4ai_heuristic_entries",
]
