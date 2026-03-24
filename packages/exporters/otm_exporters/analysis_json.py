"""Serialização JSON do resultado de análise (`AnalysisResult`)."""

from __future__ import annotations

from typing import Any

from otm_threat_engine import AnalysisResult


def export_analysis_json(result: AnalysisResult, *, indent: int = 2) -> str:
    """JSON do motor (heurísticas, summary, achados)."""
    return result.model_dump_json(indent=indent)


def export_analysis_json_obj(result: AnalysisResult) -> dict[str, Any]:
    return result.model_dump(mode="json")
