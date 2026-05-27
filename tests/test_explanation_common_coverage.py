"""Coverage — explanation label helpers + methodology-lens common token/AI helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from otm_core_schema import ThreatModelDocument, create_blank_document, load_document_from_yaml_path
from otm_threat_engine.explanation_builders import _asset_note, _comp_label
from otm_threat_engine.methodology_lenses.common import (
    has_any_token,
    has_safe_ai_marker,
    has_token,
    looks_like_ai_context,
)

_ROOT = Path(__file__).resolve().parents[1]
_DOC = _ROOT / "examples" / "saas-ordering-v1.otm.yaml"


def test_comp_label_variants() -> None:
    doc = load_document_from_yaml_path(_DOC)
    assert _comp_label(doc, None) is None
    cid = doc.components[0].id
    assert _comp_label(doc, cid) == f"{doc.components[0].name} ({cid})"
    assert _comp_label(doc, "ghost_id") == "ghost_id"  # not found -> returns id


def test_asset_note_variants() -> None:
    doc = load_document_from_yaml_path(_DOC)
    assert _asset_note(doc, None) is None
    assert _asset_note(doc, "ghost_asset") is None  # not found -> None
    if doc.assets:
        note = _asset_note(doc, doc.assets[0].id)
        assert note and "ativo" in note


def test_has_token_empty() -> None:
    assert has_token("some text", "") is False
    assert has_token("an llm system", "llm") is True


def test_has_any_token() -> None:
    assert has_any_token("uses rag pipeline", ("rag",)) is True
    assert has_any_token("plain text", ("llm", "rag")) is False


def test_looks_like_ai_context_via_marker() -> None:
    d: dict[str, Any] = create_blank_document().model_dump(mode="python", by_alias=True)
    d.setdefault("metadata", {})["summary"] = "model inference agent pipeline for predictions"
    doc = ThreatModelDocument.model_validate(d)
    assert looks_like_ai_context(doc) is True


def test_has_safe_ai_marker() -> None:
    assert isinstance(has_safe_ai_marker("model inference agent"), bool)
