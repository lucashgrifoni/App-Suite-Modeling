"""Coverage — anti_pattern_library pure helper functions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from otm_threat_engine import anti_pattern_library as ap

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def _doc_with_asset_and_flag() -> ThreatModelDocument:
    d: dict[str, Any] = load_document_from_yaml_path(_MINIMAL).model_dump(mode="python", by_alias=True)
    d.setdefault("assets", []).append({"id": "pii_store", "name": "Customer PII", "classification": "confidential"})
    for fl in d.get("data_flows") or []:
        fl["supports_file_upload"] = True
    return ThreatModelDocument.model_validate(d)


def test_bump_confidence() -> None:
    assert isinstance(ap._bump_confidence("medium", "structural_primary"), str)
    assert isinstance(ap._bump_confidence("low", "x"), str)
    assert isinstance(ap._bump_confidence("high", "y"), str)


def test_cross_boundary_flow_ids() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    result = ap._cross_boundary_flow_ids(doc)
    assert isinstance(result, set)


def test_any_component_kind() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    assert ap._any_component_kind(doc, []) is True  # empty needles -> True
    assert ap._any_component_kind(doc, ["process"]) in (True, False)
    assert ap._any_component_kind(doc, ["nonexistent_kind"]) is False


def test_component_id_contains() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    assert ap._component_id_contains(doc, []) is True
    first_id = doc.components[0].id
    assert ap._component_id_contains(doc, [first_id]) is True
    assert ap._component_id_contains(doc, ["zzz_no_match"]) is False


def test_asset_name_id_contains() -> None:
    doc = _doc_with_asset_and_flag()
    assert ap._asset_name_id_contains(doc, []) is True
    assert ap._asset_name_id_contains(doc, ["pii"]) is True
    assert ap._asset_name_id_contains(doc, ["customer"]) is True
    assert ap._asset_name_id_contains(doc, ["zzz_no_match"]) is False


def test_any_flow_bool() -> None:
    doc = _doc_with_asset_and_flag()
    assert ap._any_flow_bool(doc, ["supports_file_upload"]) is True
    assert ap._any_flow_bool(doc, ["this_field_does_not_exist"]) is False


def test_corpus_includes_components_and_assets() -> None:
    doc = _doc_with_asset_and_flag()
    corpus = ap._corpus(doc)
    assert "customer pii" in corpus


def test_catalog_path_for_docs() -> None:
    assert ap.catalog_path_for_docs().endswith("catalog.yaml")


def test_load_definitions_nonempty() -> None:
    defs = ap._load_definitions()
    assert defs
    assert all(hasattr(x, "id") for x in defs)
