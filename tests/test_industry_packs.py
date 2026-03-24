"""Templates e industry packs."""

from __future__ import annotations

from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_industry_packs.loader import load_pack, load_template_yaml
from otm_threat_engine import ThreatAnalysisEngine

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_load_finance_pack() -> None:
    p = load_pack("finance")
    assert p.id == "finance"
    assert p.risk_tuning is not None
    assert p.additional_threats


def test_analyze_with_pack_increases_risk_or_adds_threats() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    base = ThreatAnalysisEngine().analyze(doc, pack=None)
    fin = ThreatAnalysisEngine().analyze(doc, pack=load_pack("finance"))
    assert fin.summary.pack_threats_generated >= 1
    assert fin.industry_pack_id == "finance"
    assert fin.pack_control_hints
    assert base.industry_pack_id is None


def test_template_yaml_loads() -> None:
    from otm_core_schema.io import load_document_from_yaml

    raw = load_template_yaml("saas-web")
    assert "saas" in raw.lower()
    d = load_document_from_yaml(raw)
    assert d.metadata.title
    assert len(d.components) >= 1
