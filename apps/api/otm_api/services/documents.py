"""Carregar e criar documentos canónicos (sem HTTP)."""

from __future__ import annotations

from typing import Any

from otm_core_schema import (
    ThreatModelDocument,
    load_document_from_dict,
    load_document_from_yaml,
)
from otm_core_schema import (
    create_blank_document as create_blank_document_from_schema,
)
from otm_industry_packs.loader import load_template_yaml


def create_blank_document() -> ThreatModelDocument:
    """Novo modelo mínimo válido."""
    return create_blank_document_from_schema()


def document_from_payload(data: dict[str, Any]) -> ThreatModelDocument:
    """Valida dict contra o schema canónico."""
    return load_document_from_dict(data)


def document_from_template(template_id: str) -> ThreatModelDocument:
    """
    Instancia um template embutido.
    Raises:
        FileNotFoundError: template desconhecido.
        PydanticValidationError: YAML inválido.
    """
    yaml_text = load_template_yaml(template_id)
    return load_document_from_yaml(yaml_text)


__all__ = [
    "create_blank_document",
    "document_from_payload",
    "document_from_template",
]
