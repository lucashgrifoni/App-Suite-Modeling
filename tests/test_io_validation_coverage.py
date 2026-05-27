"""Coverage — YAML/JSON loading validation raises and schema helpers."""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_artifact_import._yamljson import load_object_from_text
from otm_core_schema import create_blank_document
from otm_core_schema.io import dump_document_to_json, json_schema, load_document_from_yaml


def test_yamljson_empty_raises() -> None:
    with pytest.raises(ValueError):
        load_object_from_text("")


def test_yamljson_non_mapping_raises() -> None:
    with pytest.raises(ValueError):
        load_object_from_text("- a\n- b\n")


def test_yamljson_unparseable_raises() -> None:
    with pytest.raises(ValueError):
        load_object_from_text("a: : : :\n\t- broken")


def test_yamljson_ok() -> None:
    assert load_object_from_text("a: 1\nb: 2\n") == {"a": 1, "b": 2}


def test_core_io_yaml_root_not_mapping() -> None:
    with pytest.raises(ValueError):
        load_document_from_yaml("- not\n- mapping\n")


def test_core_io_dump_json_and_schema() -> None:
    doc = create_blank_document()
    assert dump_document_to_json(doc).startswith("{")
    schema = json_schema()
    assert isinstance(schema, dict) and "properties" in schema or "$defs" in schema


def test_cli_io_util_errors(tmp_path: Path) -> None:
    from otm_cli.io_util import load_doc

    bad = tmp_path / "bad.otm.yaml"
    bad.write_text("a: : : invalid\n\t-\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        load_doc(bad)

    not_mapping = tmp_path / "list.otm.yaml"
    not_mapping.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(RuntimeError):
        load_doc(not_mapping)

    with pytest.raises(RuntimeError):
        load_doc(tmp_path / "missing.otm.yaml")


def test_compare_body_partial_analysis_rejected() -> None:
    pytest.importorskip("fastapi")
    from otm_api.schemas.bodies import CompareBody

    doc = create_blank_document().model_dump(mode="json", by_alias=True)
    with pytest.raises(Exception):
        CompareBody.model_validate({"document": doc, "baseline": doc, "baseline_analysis": {"x": 1}})
