"""Artefatos iniciais canônicos reutilizáveis (CLI/API)."""

from __future__ import annotations

from otm_core_schema.document import ThreatModelDocument
from otm_core_schema.io import load_document_from_yaml

BLANK_DOCUMENT_YAML = """# Gerado por: otm init
model:
  schema_version: "1.0.0"
  system_type: web_application
  industry_sector: generic

metadata:
  title: "Novo threat model"
  summary: "Edite este arquivo e rode: otm validate ."

trust_boundaries: []
components: []
data_flows: []
assets: []
threats: []
mitigations: []
evidence_suggestions: []
"""


def create_blank_document() -> ThreatModelDocument:
    """Novo modelo mínimo válido (fonte única para CLI/API)."""
    return load_document_from_yaml(BLANK_DOCUMENT_YAML)
