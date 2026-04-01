"""
Serialização JSON do resultado de análise (`AnalysisResult`).

Regressão: `tests/test_exporters.py` (`analysis_json`, `summary`, heurísticas).
"""

from __future__ import annotations

import json
from typing import Any

from otm_threat_engine import AnalysisResult


def export_analysis_json_obj(result: AnalysisResult) -> dict[str, Any]:
    """Objeto JSON-compatível; ordem das chaves segue `AnalysisResult` (ver `test_exporters`)."""
    return result.model_dump(mode="json")


def export_analysis_json(result: AnalysisResult, *, indent: int = 2) -> str:
    """JSON do motor (heurísticas, summary, achados)."""
    return json.dumps(export_analysis_json_obj(result), indent=indent, ensure_ascii=False)
