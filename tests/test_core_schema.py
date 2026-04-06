"""Testes do schema canônico."""

from pathlib import Path

import pytest
from otm_core_schema import (
    dump_document_to_yaml,
    load_document_from_yaml,
    load_document_from_yaml_path,
)
from otm_core_schema.enums import ThreatModelMethodology

_ROOT = Path(__file__).resolve().parents[1]
_EXAMPLE_MIN = _ROOT / "examples" / "minimal.otm.yaml"
_EXAMPLE_SAAS = _ROOT / "examples" / "saas-ordering-v1.otm.yaml"


def test_load_minimal_example() -> None:
    doc = load_document_from_yaml_path(_EXAMPLE_MIN)
    assert doc.metadata.title
    assert doc.model_info.schema_version == "1.1.0"
    assert len(doc.components) == 4


def test_load_realistic_example() -> None:
    doc = load_document_from_yaml_path(_EXAMPLE_SAAS)
    assert doc.business_context is not None
    assert len(doc.assets) >= 1
    assert len(doc.threats) == 2
    assert doc.threats[0].treatment_status.value == "triaged"
    assert len(doc.evidence_suggestions) == 3


def test_roundtrip_yaml() -> None:
    doc = load_document_from_yaml_path(_EXAMPLE_MIN)
    text = dump_document_to_yaml(doc)
    again = load_document_from_yaml(text)
    assert again.model_dump() == doc.model_dump()


def test_invalid_reference_raises() -> None:
    raw = """
model:
  schema_version: "1.0.0"
metadata:
  title: "x"
components:
  - id: a
    name: "A"
    kind: process
data_flows:
  - id: f
    from_component: a
    to_component: missing
"""
    with pytest.raises(Exception):
        load_document_from_yaml(raw)


def test_invalid_flow_reference_error_message_is_clear() -> None:
    raw = """
model:
  schema_version: "1.0.0"
metadata:
  title: "x"
components:
  - id: a
    name: "A"
    kind: process
data_flows:
  - id: f
    from_component: a
    to_component: missing
"""
    with pytest.raises(ValueError, match=r"data_flow 'f' to_component 'missing' not found"):
        load_document_from_yaml(raw)


def test_invalid_component_trust_boundary_reference_message_is_clear() -> None:
    raw = """
model:
  schema_version: "1.0.0"
metadata:
  title: "x"
components:
  - id: a
    name: "A"
    kind: process
    in_trust_boundary: tb_missing
data_flows: []
trust_boundaries: []
assets: []
threats: []
mitigations: []
evidence_suggestions: []
"""
    with pytest.raises(
        ValueError,
        match=r"component 'a' references unknown trust boundary 'tb_missing'",
    ):
        load_document_from_yaml(raw)


def test_methodology_default_is_stride() -> None:
    doc = load_document_from_yaml_path(_EXAMPLE_MIN)
    assert doc.model_info.methodology == ThreatModelMethodology.STRIDE


def test_schema_contract_accepts_model_alias() -> None:
    raw = """
model:
  schema_version: "1.0.0"
  system_type: web_application
  industry_sector: generic
  methodology: stride
metadata:
  title: "alias-check"
components: []
data_flows: []
assets: []
threats: []
mitigations: []
evidence_suggestions: []
"""
    doc = load_document_from_yaml(raw)
    assert doc.model_info.schema_version == "1.0.0"
    assert doc.model_info.methodology == ThreatModelMethodology.STRIDE


def test_schema_contract_rejects_extra_root_fields() -> None:
    raw = """
model:
  schema_version: "1.0.0"
metadata:
  title: "x"
components: []
data_flows: []
assets: []
threats: []
mitigations: []
evidence_suggestions: []
unexpected_root: true
"""
    with pytest.raises(Exception):
        load_document_from_yaml(raw)
