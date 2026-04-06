"""Cobertura explícita do pré-check de qualidade do modelo (minimal / good / rich)."""

from __future__ import annotations

from pathlib import Path

from otm_core_schema import assess_model_precheck, load_document_from_yaml, load_document_from_yaml_path

_ROOT = Path(__file__).resolve().parents[1]


def _minimal_model_yaml() -> str:
    """Modelo deliberadamente pobre: sem ativos, sem fronteiras, fluxo genérico."""
    return """
model:
  schema_version: "1.1.0"
  methodology: stride
metadata:
  title: "Precheck minimal"
components:
  - id: a
    name: "A"
    kind: process
  - id: b
    name: "B"
    kind: process
data_flows:
  - id: f1
    from_component: a
    to_component: b
assets: []
trust_boundaries: []
threats: []
mitigations: []
evidence_suggestions: []
"""


def _rich_model_yaml() -> str:
    """Modelo com vários sinais de riqueza (alvo: banda rich / score alto)."""
    return """
model:
  schema_version: "1.1.0"
  methodology: stride
metadata:
  title: "Precheck rich"
business_context:
  description: "Sistema com objetivos explícitos."
  business_objectives:
    - "Disponibilidade do serviço"
  business_goals: []
  security_objectives: []
  stakeholders: []
  assumptions: []
  critical_integrations: []
trust_boundaries:
  - id: internet
    name: Internet
  - id: vpc
    name: VPC
    member_component_ids: [api, db]
components:
  - id: user
    name: User
    kind: user
    in_trust_boundary: internet
  - id: api
    name: API
    kind: process
    responsibility: public_api
    privilege_level: high
    in_trust_boundary: vpc
    asset_ids: [data1]
  - id: db
    name: DB
    kind: datastore
    in_trust_boundary: vpc
    asset_ids: [data1]
data_flows:
  - id: ingress
    name: HTTPS
    from_component: user
    to_component: api
    protocol: HTTPS
    public_exposure: true
    semantic_class: public_api_ingress_flow
  - id: todb
    from_component: api
    to_component: db
    protocol: TCP
    semantic_class: storage_processing_flow
    stores_sensitive_data: true
assets:
  - id: data1
    name: "Dados classificados"
    asset_kind: data
    data_classification: confidential
    business_criticality: high
    related_component_ids: [api, db]
    related_data_flow_ids: [todb]
threats: []
mitigations: []
evidence_suggestions: []
"""


def test_precheck_minimal_band_and_low_confidence() -> None:
    doc = load_document_from_yaml(_minimal_model_yaml())
    p = assess_model_precheck(doc)
    assert p.band == "minimal"
    assert p.score_0_100 < 45
    assert p.recommendation_confidence == "low"
    codes = {c.code for c in p.checks}
    assert "assets_present" in codes
    assert "trust_boundaries" in codes
    assert p.methodology_fit_matrix.get("stride") in ("strong", "partial", "weak")


def test_precheck_good_from_example_minimal_otm() -> None:
    """Exemplo mínimo do repo é um bom modelo (não 'minimal' de score)."""
    doc = load_document_from_yaml_path(_ROOT / "examples" / "minimal.otm.yaml")
    p = assess_model_precheck(doc)
    assert p.band in ("good", "rich")
    assert p.score_0_100 >= 45
    assert any(c.code == "assets_present" and c.passed for c in p.checks)
    assert any(c.code == "trust_boundaries" and c.passed for c in p.checks)
    assert "flow_semantics" in {c.code for c in p.checks}


def test_precheck_rich_high_score_and_strong_stride_fit() -> None:
    doc = load_document_from_yaml(_rich_model_yaml())
    p = assess_model_precheck(doc)
    assert p.band == "rich"
    assert p.score_0_100 >= 75
    assert p.methodology_fit_matrix.get("stride") == "strong"
    assert p.recommendation_confidence in ("high", "medium")
