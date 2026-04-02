"""Artefatos iniciais canônicos reutilizáveis (CLI/API)."""

from __future__ import annotations

from otm_core_schema.document import ThreatModelDocument
from otm_core_schema.io import load_document_from_yaml

BLANK_DOCUMENT_YAML = """# Gerado por: otm init
model:
  schema_version: "1.1.0"
  system_type: web_application
  industry_sector: generic

metadata:
  title: "Novo threat model"
  summary: "Edite este arquivo e rode: otm validate ."

trust_boundaries:
  - id: default_perimeter
    name: "Perímetro (editar)"
    inference_note: "Fronteira inicial — ajuste membros e fluxos cruzados."

components: []
data_flows: []
assets:
  - id: svc_primary_data
    name: "Dados operacionais do serviço"
    asset_kind: data
    sensitivity: internal
    business_criticality: medium
  - id: svc_identity_context
    name: "Contexto de identidade / sessão"
    asset_kind: session
    sensitivity: confidential
    business_criticality: high
threats: []
mitigations: []
evidence_suggestions: []
"""


def create_blank_document() -> ThreatModelDocument:
    """Novo modelo mínimo válido (fonte única para CLI/API)."""
    return load_document_from_yaml(BLANK_DOCUMENT_YAML)
