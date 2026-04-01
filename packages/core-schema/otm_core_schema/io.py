"""Serialização YAML/JSON do documento canônico — sem lógica de negócio."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from otm_core_schema.document import ThreatModelDocument


def load_document_from_dict(data: dict[str, Any]) -> ThreatModelDocument:
    return ThreatModelDocument.model_validate(data)


def load_document_from_yaml(text: str) -> ThreatModelDocument:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("YAML root must be a mapping")
    return ThreatModelDocument.model_validate(data)


def load_document_from_yaml_path(path: Path | str) -> ThreatModelDocument:
    p = Path(path)
    return load_document_from_yaml(p.read_text(encoding="utf-8"))


def dump_document_to_yaml(document: ThreatModelDocument) -> str:
    # default_flow_style=False para legibilidade humana (TaC)
    data = document.model_dump(mode="json", exclude_none=True, by_alias=True)
    return yaml.safe_dump(data, sort_keys=False, allow_unicode=True, default_flow_style=False)


def dump_document_to_json(document: ThreatModelDocument, *, indent: int | None = 2) -> str:
    return document.model_dump_json(exclude_none=True, indent=indent, by_alias=True)


def json_schema() -> dict[str, Any]:
    """JSON Schema gerado a partir do modelo Pydantic (contrato e validação cruzada)."""
    return ThreatModelDocument.model_json_schema()
