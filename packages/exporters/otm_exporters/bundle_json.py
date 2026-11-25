"""
JSON combinado documento + análise (um ficheiro para CI/CD e integrações).

Contrato de chaves e paridade objeto/string: `tests/test_exporters.py` (`bundle`).
"""

from __future__ import annotations

import json
from typing import Any

from otm_core_schema import ThreatModelDocument
from otm_threat_engine import AnalysisResult

from otm_exporters.analysis_json import export_analysis_json_obj
from otm_exporters.document_json import export_document_json_obj


def export_bundle_json(
    *,
    document: dict[str, Any] | None = None,
    analysis: dict[str, Any] | None = None,
    indent: int = 2,
) -> str:
    """Payload genérico; na string JSON as chaves aparecem nesta ordem: `document`, `analysis`."""
    payload: dict[str, Any] = {
        "document": document,
        "analysis": analysis,
    }
    return json.dumps(payload, indent=indent, ensure_ascii=False, allow_nan=False)


def export_threat_model_bundle_obj(
    doc: ThreatModelDocument,
    result: AnalysisResult | None = None,
) -> dict[str, Any]:
    """Bundle com chaves nesta ordem: `document`, `analysis` (ver `test_exporters`)."""
    return {
        "document": export_document_json_obj(doc),
        "analysis": export_analysis_json_obj(result) if result is not None else None,
    }


def export_threat_model_bundle_json(
    doc: ThreatModelDocument,
    result: AnalysisResult | None = None,
    *,
    indent: int = 2,
) -> str:
    """Documento canónico + resultado de análise num único JSON."""
    return json.dumps(
        export_threat_model_bundle_obj(doc, result),
        indent=indent,
        ensure_ascii=False,
        allow_nan=False,
    )
