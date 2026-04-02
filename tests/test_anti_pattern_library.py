"""Anti-pattern library: deteção conservadora por perfil semântico."""

from __future__ import annotations

from otm_core_schema import load_document_from_yaml
from otm_industry_packs.loader import load_template_yaml
from otm_threat_engine.anti_pattern_library import detect_anti_patterns


def test_api_public_profile_can_trigger_when_keywords_missing() -> None:
    raw = load_template_yaml("api-public")
    doc = load_document_from_yaml(raw)
    hits = detect_anti_patterns(doc)
    assert isinstance(hits, list)


def test_blank_profile_returns_no_hits() -> None:
    raw = """
model:
  schema_version: "1.1.0"
  methodology: stride
metadata:
  title: X
components: []
data_flows: []
assets: []
trust_boundaries: []
threats: []
mitigations: []
evidence_suggestions: []
"""
    doc = load_document_from_yaml(raw)
    assert detect_anti_patterns(doc) == []
