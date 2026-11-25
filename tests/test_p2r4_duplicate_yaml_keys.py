"""A duplicate YAML key must not silently delete half the model.

YAML lets the last occurrence of a key win, silently. In a `.otm.yaml` that means a badly
resolved merge conflict — two `components:` blocks, two `metadata:` sections — passed
`otm validate` with the green panel while the first block was discarded: its components did
not exist, the threats that depended on them were never generated, and the report that came
out looked complete. That is precisely the class of error the pre-commit hook the README
advertises exists to catch.

Reproduced before the fix: a document with two `components:` blocks validated with exit 0 and
`Components: 1`, and `otm export --format json` showed only the second block's component.
"""

from __future__ import annotations

import pytest
from otm_core_schema import load_document_from_yaml
from otm_core_schema.io import safe_load_bounded

_DUPLICATE_COMPONENTS = """
model:
  schema_version: "1.1.0"
  system_type: web_application
  industry_sector: saas
metadata:
  title: "Badly resolved merge"
components:
  - id: api
    name: API
    kind: process
components:
  - id: db
    name: DB
    kind: datastore
"""

_DUPLICATE_METADATA = """
model:
  schema_version: "1.1.0"
  system_type: web_application
  industry_sector: saas
metadata:
  title: "First title"
metadata:
  title: "Second title"
components:
  - id: api
    name: API
    kind: process
"""

_DUPLICATE_NESTED_KEY = """
model:
  schema_version: "1.1.0"
  system_type: web_application
  industry_sector: saas
metadata:
  title: "Nested duplicate"
components:
  - id: api
    name: API
    name: Renamed API
    kind: process
"""


def test_a_duplicated_top_level_block_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate key 'components'"):
        load_document_from_yaml(_DUPLICATE_COMPONENTS)


def test_the_error_names_the_line_so_the_merge_can_be_found() -> None:
    with pytest.raises(ValueError, match=r"line \d+, column \d+"):
        load_document_from_yaml(_DUPLICATE_COMPONENTS)


def test_the_error_explains_what_yaml_would_have_done() -> None:
    with pytest.raises(ValueError, match="only the last block"):
        load_document_from_yaml(_DUPLICATE_COMPONENTS)


def test_a_duplicated_metadata_block_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate key 'metadata'"):
        load_document_from_yaml(_DUPLICATE_METADATA)


def test_a_duplicate_inside_a_nested_mapping_is_rejected() -> None:
    """The first `name` was dropped just as silently as a top-level block."""
    with pytest.raises(ValueError, match="duplicate key 'name'"):
        load_document_from_yaml(_DUPLICATE_NESTED_KEY)


def test_the_shared_loader_rejects_duplicates_for_artifact_imports_too() -> None:
    """`safe_load_bounded` is the loader the HTTP artifact importers use."""
    with pytest.raises(ValueError, match="duplicate key 'a'"):
        safe_load_bounded("a: 1\na: 2\n")


def test_a_repeated_value_under_distinct_keys_is_not_a_duplicate() -> None:
    assert safe_load_bounded("a: 1\nb: 1\n") == {"a": 1, "b": 1}


def test_the_same_key_in_sibling_mappings_is_not_a_duplicate() -> None:
    """`name` appears twice in the document, but once per mapping — that is normal."""
    loaded = safe_load_bounded("- name: one\n- name: two\n")

    assert loaded == [{"name": "one"}, {"name": "two"}]


def test_a_yaml_merge_key_is_not_a_duplicate() -> None:
    """`<<` has no constructor of its own, and two merges into sibling mappings are legal."""
    loaded = safe_load_bounded(
        "defaults: &defaults\n  kind: process\nfirst:\n  <<: *defaults\nsecond:\n  <<: *defaults\n"
    )

    assert loaded["first"] == {"kind": "process"}
    assert loaded["second"] == {"kind": "process"}


def test_an_anchor_override_is_not_a_duplicate() -> None:
    """Overriding an inherited key is the whole point of a merge — it must not be refused."""
    loaded = safe_load_bounded("defaults: &d\n  kind: process\nsvc:\n  <<: *d\n  kind: datastore\n")

    assert loaded["svc"]["kind"] == "datastore"


def test_a_valid_document_still_loads() -> None:
    doc = load_document_from_yaml(
        "model:\n"
        '  schema_version: "1.1.0"\n'
        "  system_type: web_application\n"
        "  industry_sector: saas\n"
        "metadata:\n"
        '  title: "Clean"\n'
        "components:\n"
        "  - id: api\n"
        "    name: API\n"
        "    kind: process\n"
    )

    assert [c.id for c in doc.components] == ["api"]
