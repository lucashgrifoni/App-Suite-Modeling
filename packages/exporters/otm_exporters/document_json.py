"""Serialização JSON do documento canónico (pipelines, integrações)."""

from __future__ import annotations

import json
from typing import Any

from otm_core_schema import ThreatModelDocument


def export_document_json(doc: ThreatModelDocument, *, indent: int = 2) -> str:
    """JSON estável com alias de schema e campos nulos omitidos."""
    return doc.model_dump_json(by_alias=True, exclude_none=True, indent=indent)


def export_document_json_obj(doc: ThreatModelDocument) -> dict[str, Any]:
    """Objeto Python (para compor payloads ou testes)."""
    return doc.model_dump(by_alias=True, exclude_none=True, mode="json")
