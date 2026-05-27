"""Coverage — small engine helpers (severity buckets, component-kind lookup)."""

from __future__ import annotations

from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_threat_engine.remediation.classify import component_kind_for_id
from otm_threat_engine.risk_aggregate import _severity_bucket

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_severity_buckets_all_ranges() -> None:
    assert _severity_bucket(25) == "critical"
    assert _severity_bucket(20) == "critical"
    assert _severity_bucket(12) == "high"
    assert _severity_bucket(6) == "medium"
    assert _severity_bucket(5.9) == "low"
    assert _severity_bucket(0) == "low"


def test_component_kind_for_id_variants() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    assert component_kind_for_id(None, "anything") is None
    assert component_kind_for_id(doc, None) is None
    assert component_kind_for_id(doc, "does_not_exist") is None
    first = doc.components[0]
    assert component_kind_for_id(doc, first.id) == first.kind
