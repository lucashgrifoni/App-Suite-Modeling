"""
Serialização JSON do documento canónico (pipelines, integrações).

Contratos / ordem de chaves: `tests/test_exporters.py` (`document_json`, `nested_entity`).
"""

from __future__ import annotations

import json
from typing import Any

from otm_core_schema import ThreatModelDocument


def export_document_json_obj(doc: ThreatModelDocument) -> dict[str, Any]:
    """
    Objeto JSON-compatível; ordem das chaves segue `ThreatModelDocument` com aliases
    (`exclude_none`, `test_exporters`).
    """
    return doc.model_dump(mode="json", by_alias=True, exclude_none=True)


def export_document_json(doc: ThreatModelDocument, *, indent: int = 2) -> str:
    """JSON estável com alias de schema e campos nulos omitidos (UTF-8 literal)."""
    return json.dumps(export_document_json_obj(doc), indent=indent, ensure_ascii=False, allow_nan=False)
