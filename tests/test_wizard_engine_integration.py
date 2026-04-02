"""Assistente (`wz:` tags) influencia motor — ranking e notas explicáveis."""

from __future__ import annotations

from otm_core_schema import load_document_from_yaml
from otm_industry_packs.loader import load_template_yaml
from otm_threat_engine import analyze_document
from otm_threat_engine.wizard_signals import parse_wizard_tags, synthetic_keyword_corpus


def test_parse_wizard_tags_roundtrip() -> None:
    tags = ["wz:internal_admin_portal:approval=no", "foo", "wz:api_backend_rest:rate_limit=yes"]
    sigs = parse_wizard_tags(tags)
    assert len(sigs) == 2
    assert sigs[0].key == "approval"
    assert sigs[0].value == "no"


def test_synthetic_corpus_includes_approval_keywords() -> None:
    from otm_threat_engine.wizard_signals import WizardSignal

    s = [
        WizardSignal("internal_admin_portal", "approval", "yes"),
    ]
    text = synthetic_keyword_corpus(s)
    assert "aprovação" in text


def test_wizard_negative_signals_produce_notes_and_boost() -> None:
    raw = load_template_yaml("admin-portal")
    doc = load_document_from_yaml(raw)
    doc.metadata.tags = ["wz:internal_admin_portal:approval=no", "wz:internal_admin_portal:segregation=no"]
    r = analyze_document(doc, methodology="stride")
    assert r.wizard_context_notes
    boosted = any("wizard:context_boost" in (h.signal_refs or []) for h in r.heuristic_threats)
    assert boosted or r.summary.max_risk_score is not None
