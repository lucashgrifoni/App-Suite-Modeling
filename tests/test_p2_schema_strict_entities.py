"""An unknown key inside a nested entity is an error, not silent data loss.

Only the root document forbade extra keys, so a one-character typo on a nested entity
(`in_trust_boundry`, `encripted`) loaded clean, left the real field at its default and changed
the analysis: one variant deleted a STRIDE tampering threat, the other invented an information
disclosure threat. `otm validate` — the command whose whole job is to certify the document —
printed the green "Valid" panel and exited 0 in both cases.

`docs/features/SCHEMA_V1.md` §1 points extensibility at the nested `metadata: dict`, so loose
unknown keys were an oversight rather than a forward-compatibility escape hatch. Forbidding
them on every entity is a **breaking schema change**: a document carrying extra keys now fails
validation instead of having them dropped.

The same file covers `model.schema_version`, which accepted `abc`, `""` and `2.0.0` while
`validate` echoed the value back inside the green panel as if it had been checked.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from otm_core_schema import load_document_from_yaml, load_document_from_yaml_path
from otm_core_schema.document import (
    Asset,
    BusinessContext,
    Component,
    DataFlow,
    EvidenceSuggestion,
    Metadata,
    Mitigation,
    ModelInfo,
    ResidualRiskSummary,
    RiskAssessment,
    Threat,
    ThreatModelDocument,
    TrustBoundary,
)
from otm_core_schema.version import CANONICAL_SCHEMA_VERSION
from otm_threat_engine import analyze_document
from pydantic import ValidationError

_MINIMAL = Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml"

_EXTRA_FORBIDDEN = "Extra inputs are not permitted"


@pytest.fixture
def minimal_text() -> str:
    return _MINIMAL.read_text(encoding="utf-8")


def _errors(exc_info: pytest.ExceptionInfo[ValidationError]) -> list[dict[str, Any]]:
    return exc_info.value.errors()


@pytest.mark.parametrize(
    ("original", "typo", "path"),
    [
        ("in_trust_boundary: internet", "in_trust_boundry: internet", "components.0.in_trust_boundry"),
        ("encrypted: true", "encripted: true", "data_flows.0.encripted"),
        ("authenticated: true", "authenticaded: true", "data_flows.0.authenticaded"),
        ("semantic_class: public_api_ingress_flow", "semantic_clas: x", "data_flows.0.semantic_clas"),
        ("member_component_ids:", "member_component_id:", "trust_boundaries.1.member_component_id"),
        ("stores_sensitive_data: true", "stores_sensitive_dat: true", "data_flows.2.stores_sensitive_dat"),
        ("data_classification: confidential", "data_classificaton: confidential", "assets.0.data_classificaton"),
    ],
)
def test_a_misspelled_nested_field_is_rejected_and_named(
    minimal_text: str, original: str, typo: str, path: str
) -> None:
    """The diagnostic has to name the offending key and its path, like the root rejection does."""
    with pytest.raises(ValidationError, match=_EXTRA_FORBIDDEN) as exc_info:
        load_document_from_yaml(minimal_text.replace(original, typo))

    reported = {".".join(str(part) for part in e["loc"]) for e in _errors(exc_info)}
    assert path in reported


def test_the_typo_diagnostic_says_extra_inputs_are_not_permitted(minimal_text: str) -> None:
    with pytest.raises(ValidationError, match=_EXTRA_FORBIDDEN):
        load_document_from_yaml(minimal_text.replace("in_trust_boundary: internet", "in_trust_boundry: internet"))


def test_an_arbitrary_unknown_key_under_model_is_rejected(minimal_text: str) -> None:
    """`model:` was as permissive as the entities: `totally_unknown_key: 42` loaded silently."""
    mutated = minimal_text.replace('schema_version: "1.1.0"', 'schema_version: "1.1.0"\n  totally_unknown_key: 42')

    with pytest.raises(ValidationError, match=_EXTRA_FORBIDDEN):
        load_document_from_yaml(mutated)


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (Metadata, {"title": "t", "nope": 1}),
        (BusinessContext, {"nope": 1}),
        (ModelInfo, {"nope": 1}),
        (Asset, {"id": "a", "name": "A", "nope": 1}),
        (Component, {"id": "c", "name": "C", "kind": "process", "nope": 1}),
        (DataFlow, {"id": "f", "from_component": "a", "to_component": "b", "nope": 1}),
        (TrustBoundary, {"id": "tb", "name": "TB", "nope": 1}),
        (RiskAssessment, {"likelihood": 1, "impact": 1, "nope": 1}),
        (ResidualRiskSummary, {"nope": 1}),
        (EvidenceSuggestion, {"id": "e", "title": "E", "nope": 1}),
        (Mitigation, {"id": "m", "title": "M", "nope": 1}),
        (Threat, {"id": "t", "title": "T", "stride": "tampering", "nope": 1}),
    ],
)
def test_every_canonical_entity_forbids_unknown_keys(model: type, payload: dict[str, Any]) -> None:
    """One permissive entity is enough to reopen the hole, so the rule is asserted on all of them."""
    with pytest.raises(ValidationError, match=_EXTRA_FORBIDDEN):
        model.model_validate(payload)


def test_the_documented_metadata_bag_still_accepts_anything() -> None:
    """Extensibility moved, it did not disappear: `metadata` is the documented escape hatch."""
    component = Component.model_validate(
        {"id": "c", "name": "C", "kind": "process", "metadata": {"anything": {"nested": [1, 2]}}}
    )

    assert component.metadata == {"anything": {"nested": [1, 2]}}


def test_the_stock_example_still_validates() -> None:
    """Forbidding unknown keys must not reject the models the product ships."""
    doc = load_document_from_yaml_path(_MINIMAL)

    assert len(doc.components) == 4


def test_the_tampering_threat_the_typo_used_to_delete_is_present_in_the_stock_model() -> None:
    """Anchors why this matters: the typo'd model analysed as if the field had been deleted."""
    result = analyze_document(load_document_from_yaml_path(_MINIMAL))

    assert "eng_flow_http_in_tampering" in {t.id for t in result.heuristic_threats}


@pytest.mark.parametrize("bad", ["abc", "", "1.1", "1", "v1.1.0", "1.1.0.0", "01.1.0"])
def test_a_non_semver_schema_version_is_rejected(bad: str) -> None:
    with pytest.raises(ValidationError, match="must be semver"):
        ModelInfo.model_validate({"schema_version": bad})


@pytest.mark.parametrize("unsupported", ["2.0.0", "99.99.99", "0.9.0"])
def test_a_schema_version_from_another_major_is_rejected(unsupported: str) -> None:
    """A 2.x document validated against 1.x rules is the silent-wrong-result case, not a warning."""
    with pytest.raises(ValidationError, match="this engine implements schema"):
        ModelInfo.model_validate({"schema_version": unsupported})


@pytest.mark.parametrize("good", ["1.0.0", "1.1.0", "1.9.3", "1.1.0-rc1", "1.1.0+build.5"])
def test_a_supported_semver_schema_version_is_accepted(good: str) -> None:
    assert ModelInfo.model_validate({"schema_version": good}).schema_version == good


def test_the_default_schema_version_is_the_canonical_constant() -> None:
    assert ModelInfo().schema_version == CANONICAL_SCHEMA_VERSION


def test_the_bad_schema_version_is_reported_under_the_model_block(minimal_text: str) -> None:
    """`otm validate` renders the error path, so it must point at `model → schema_version`."""
    with pytest.raises(ValidationError, match="must be semver") as exc_info:
        load_document_from_yaml(minimal_text.replace('schema_version: "1.1.0"', 'schema_version: "abc"'))

    reported = {".".join(str(part) for part in e["loc"]) for e in _errors(exc_info)}
    assert "model.schema_version" in reported


def test_the_root_document_still_forbids_unknown_keys() -> None:
    """The behaviour that already worked has to keep working."""
    with pytest.raises(ValidationError, match=_EXTRA_FORBIDDEN):
        ThreatModelDocument.model_validate({"metadata": {"title": "t"}, "unknown_root_key": 1})
