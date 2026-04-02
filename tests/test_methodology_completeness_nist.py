"""Completude de metodologia — NIST Data-Centric (partial / degraded)."""

from __future__ import annotations

from otm_core_schema import (
    ThreatModelDocument,
    ThreatModelMethodology,
    load_document_from_yaml,
)
from otm_core_schema.enums import MethodologyCompletenessState
from otm_threat_engine.methodology_completeness import assess_methodology_completeness


def _nist_doc_no_assets_yaml() -> str:
    return """
model:
  schema_version: "1.1.0"
  methodology: nist_data_centric
metadata:
  title: "NIST sem ativos"
components:
  - id: x
    name: X
    kind: process
data_flows: []
assets: []
trust_boundaries: []
threats: []
mitigations: []
evidence_suggestions: []
"""


def _nist_doc_assets_unclassified_yaml() -> str:
    return """
model:
  schema_version: "1.1.0"
  methodology: nist_data_centric
metadata:
  title: "NIST com ativos sem classificação"
components:
  - id: x
    name: X
    kind: process
data_flows: []
assets:
  - id: blob
    name: "Blob sem classificação"
    asset_kind: data
trust_boundaries: []
threats: []
mitigations: []
evidence_suggestions: []
"""


def test_nist_data_centric_degraded_without_assets() -> None:
    doc = load_document_from_yaml(_nist_doc_no_assets_yaml())
    assert isinstance(doc, ThreatModelDocument)
    info = assess_methodology_completeness(doc, ThreatModelMethodology.NIST_DATA_CENTRIC)
    assert info.state == MethodologyCompletenessState.DEGRADED
    assert any("sem ativos" in r.lower() for r in info.reasons)


def test_nist_data_centric_partial_when_assets_without_data_classification() -> None:
    doc = load_document_from_yaml(_nist_doc_assets_unclassified_yaml())
    info = assess_methodology_completeness(doc, ThreatModelMethodology.NIST_DATA_CENTRIC)
    assert info.state == MethodologyCompletenessState.PARTIAL
    assert any("data_classification" in r.lower() or "classificação" in r.lower() for r in info.reasons)
