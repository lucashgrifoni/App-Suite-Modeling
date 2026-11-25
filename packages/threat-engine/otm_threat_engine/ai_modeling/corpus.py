"""Texto agregado do documento para deteção heurística de contexto IA (calibração + PLOT4ai).

A implementação vive em `otm_core_schema.ai_context`: a matriz de adequação metodologia ×
contexto (em core-schema) precisa exactamente do mesmo corpus, e core-schema não pode importar
o motor. Este módulo continua a ser o ponto de entrada usado pelo motor.
"""

from __future__ import annotations

from otm_core_schema.ai_context import build_ai_calibration_corpus

__all__ = ["build_ai_calibration_corpus"]
