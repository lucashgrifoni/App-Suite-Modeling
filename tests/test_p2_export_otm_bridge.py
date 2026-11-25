"""`otm export -f otm` must not drop security-relevant architecture on the way out.

The bridge emitted only id/name/type/parent/description per component, id/name/source/
destination/bidirectional per dataflow, and a fabricated constant `risk: 50/50/50` per asset.
So a user exporting to OTM 0.2.0 to hand to another tool lost every flow's `protocol`,
`authenticated` and `encrypted`, every component's `technology` and asset links, and every
asset's `data_classification`/`business_criticality` — with no warning of any kind. Re-analysing
the round-tripped model moved 11 of 17 risk scores down on `saas-multi-tenant` (top threat
25.0 -> 15.0) and invented 3 flow threats that the original model does not have.

OTM 0.2.0 does have somewhere to put all of it: every entity carries a free-form `attributes`
object, components carry `assets.processed`/`.stored`, and the project carries `attributes` too.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

import pytest
from otm_artifact_import.otm_native import document_to_otm, import_otm_text, otm_to_document
from otm_cli.cli import app
from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from otm_threat_engine import analyze_document
from typer.testing import CliRunner

_MINIMAL = Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml"

#: The five templates the bug was reproduced on, in both the report and the verification pass.
_TEMPLATES = ["saas-multi-tenant", "ai-rag-enterprise", "api-backend", "cloud-native", "admin-portal"]


@pytest.fixture
def minimal_doc() -> ThreatModelDocument:
    return load_document_from_yaml_path(_MINIMAL)


@pytest.fixture
def exported(minimal_doc: ThreatModelDocument) -> dict[str, Any]:
    return document_to_otm(minimal_doc)


def _by_id(entries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {e["id"]: e for e in entries}


# --------------------------------------------------------------------------- export carries it


def test_a_flow_keeps_its_protocol_on_the_way_out(exported: dict[str, Any]) -> None:
    assert _by_id(exported["dataflows"])["http_in"]["attributes"]["protocol"] == "HTTPS"


def test_a_flow_keeps_encrypted_on_the_way_out(exported: dict[str, Any]) -> None:
    assert _by_id(exported["dataflows"])["http_in"]["attributes"]["encrypted"] is True


def test_a_flow_keeps_authenticated_on_the_way_out(exported: dict[str, Any]) -> None:
    assert _by_id(exported["dataflows"])["http_in"]["attributes"]["authenticated"] is True


def test_a_flow_keeps_its_semantic_class_on_the_way_out(exported: dict[str, Any]) -> None:
    """The semantic class steers the composite heuristics; losing it invented flow threats."""
    attributes = _by_id(exported["dataflows"])["http_in"]["attributes"]

    assert attributes["semantic_class"] == "public_api_ingress_flow"


def test_a_component_keeps_its_technology_on_the_way_out(exported: dict[str, Any]) -> None:
    assert _by_id(exported["components"])["db"]["attributes"]["technology"] == "PostgreSQL"


def test_a_datastore_reports_the_assets_it_stores_in_the_otm_slot(exported: dict[str, Any]) -> None:
    """OTM has a home for this link — `component.assets.stored` — so the bridge uses it."""
    assert _by_id(exported["components"])["db"]["assets"]["stored"] == ["orders_data"]


def test_a_non_datastore_reports_the_assets_it_processes(exported: dict[str, Any]) -> None:
    assert _by_id(exported["components"])["api"]["assets"]["processed"] == ["orders_data"]


def test_asset_classification_is_no_longer_a_constant(exported: dict[str, Any]) -> None:
    """`confidential` and an unclassified asset used to receive the identical fabricated 50."""
    assets = _by_id(exported["assets"])

    assert assets["orders_data"]["risk"]["confidentiality"] != assets["session_ctx"]["risk"]["confidentiality"]


def test_the_exact_data_classification_travels_for_a_lossless_return(exported: dict[str, Any]) -> None:
    assert _by_id(exported["assets"])["orders_data"]["attributes"]["data_classification"] == "confidential"


def test_the_exact_business_criticality_travels_too(exported: dict[str, Any]) -> None:
    assert _by_id(exported["assets"])["orders_data"]["attributes"]["business_criticality"] == "high"


def test_the_canonical_model_header_travels_in_the_project_attributes(exported: dict[str, Any]) -> None:
    """`model` decides which rules read the document; defaults re-analysed it as a different model."""
    assert exported["project"]["attributes"]["model"]["industry_sector"] == "saas"


def test_an_unset_optional_field_is_not_invented_in_the_attributes(exported: dict[str, Any]) -> None:
    """`exclude_defaults` keeps the OTM file to what the modeller actually declared."""
    assert "attributes" not in _by_id(exported["components"])["worker"]


# --------------------------------------------------------------------------- round trip


@pytest.mark.parametrize("collection", ["components", "data_flows", "assets", "trust_boundaries"])
def test_the_round_trip_returns_the_same_entities(minimal_doc: ThreatModelDocument, collection: str) -> None:
    back = otm_to_document(document_to_otm(minimal_doc))
    before = [e.model_dump(mode="json") for e in getattr(minimal_doc, collection)]
    after = [e.model_dump(mode="json") for e in getattr(back, collection)]

    assert after == before


def test_the_round_trip_returns_the_same_model_header(minimal_doc: ThreatModelDocument) -> None:
    back = otm_to_document(document_to_otm(minimal_doc))

    assert back.model_info.model_dump(mode="json") == minimal_doc.model_info.model_dump(mode="json")


def test_an_unnamed_flow_does_not_come_back_named_after_its_id(minimal_doc: ThreatModelDocument) -> None:
    """OTM requires `dataflows[].name`, so the export fills it with the id — the import undoes it."""
    back = otm_to_document(document_to_otm(minimal_doc))
    flow = next(f for f in back.data_flows if f.id == "to_db")

    assert flow.name is None


@pytest.mark.parametrize("template", _TEMPLATES)
def test_the_analysis_is_unchanged_by_a_round_trip(template: str) -> None:
    """The measurable harm was here: the same engine scored the round-tripped model lower."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / f"{template}.otm.yaml"
        init = CliRunner().invoke(app, ["init", str(path), "-t", template])
        assert init.exit_code == 0, init.output
        doc = load_document_from_yaml_path(path)

    before = {t.id: t.risk.score for t in analyze_document(doc).heuristic_threats}
    after = {t.id: t.risk.score for t in analyze_document(otm_to_document(document_to_otm(doc))).heuristic_threats}

    assert after == before


# --------------------------------------------------------------------------- foreign OTM files


def _foreign(attributes: str) -> str:
    return (
        'otmVersion: "0.2.0"\n'
        "project: {id: p, name: Foreign}\n"
        "components:\n"
        f"  - {{id: api, name: API, type: web-service, attributes: {attributes}}}\n"
    )


def test_a_foreign_attribute_the_schema_does_not_know_is_ignored() -> None:
    """`attributes` is a shared bag; another tool's keys must not reach the canonical entity."""
    doc = import_otm_text(_foreign("{iriusrisk_ref: XYZ-1, technology: Django}"))

    assert doc.components[0].technology == "Django"


def test_a_canonical_key_with_the_wrong_type_is_dropped_not_fatal() -> None:
    """Dropping one bad key beats rejecting an otherwise importable file from another vendor."""
    doc = import_otm_text(_foreign("{technology: [not, a, string], responsibility: auth}"))

    assert doc.components[0].technology is None


def test_the_good_keys_beside_a_bad_one_still_arrive() -> None:
    doc = import_otm_text(_foreign("{technology: [not, a, string], responsibility: auth}"))

    assert doc.components[0].responsibility == "auth"


def test_an_attributes_value_that_is_not_a_mapping_is_ignored() -> None:
    doc = import_otm_text(_foreign("just-a-string"))

    assert doc.components[0].technology is None


def test_attributes_cannot_overwrite_an_id_and_break_referential_integrity() -> None:
    """`id`, `source` and `destination` are OTM's own slots; the bag must never win over them."""
    doc = import_otm_text(_foreign("{id: somewhere_else, name: Renamed}"))

    assert [c.id for c in doc.components] == ["api"]


def test_a_reference_to_an_asset_the_file_never_declares_is_dropped() -> None:
    """Restoring it verbatim would fail document validation and sink the whole import."""
    doc = import_otm_text(
        'otmVersion: "0.2.0"\n'
        "project: {id: p, name: Dangling}\n"
        "components:\n"
        "  - {id: api, name: API, type: web-service, assets: {processed: [ghost_asset]}}\n"
    )

    assert doc.components[0].asset_ids == []


def test_a_declared_asset_reference_survives_the_id_remapping() -> None:
    doc = import_otm_text(
        'otmVersion: "0.2.0"\n'
        "project: {id: p, name: Linked}\n"
        "components:\n"
        '  - {id: api, name: API, type: web-service, assets: {processed: ["PII Data"]}}\n'
        "assets:\n"
        '  - {id: "PII Data", name: PII}\n'
    )

    assert doc.components[0].asset_ids == [a.id for a in doc.assets]


def test_a_trust_boundary_membership_reference_is_filtered_the_same_way() -> None:
    doc = import_otm_text(
        'otmVersion: "0.2.0"\n'
        "project: {id: p, name: Members}\n"
        "trustZones:\n"
        "  - {id: tz, name: Zone, attributes: {member_component_ids: [api, ghost]}}\n"
        "components:\n"
        "  - {id: api, name: API, type: web-service, parent: {trustZone: tz}}\n"
    )

    assert doc.trust_boundaries[0].member_component_ids == ["api"]


def test_a_component_assets_block_that_is_not_a_mapping_is_ignored() -> None:
    doc = import_otm_text(
        'otmVersion: "0.2.0"\n'
        "project: {id: p, name: Odd}\n"
        "components:\n"
        "  - {id: api, name: API, type: web-service, assets: [a, b]}\n"
    )

    assert doc.components[0].asset_ids == []


def test_a_project_attributes_value_that_is_not_a_mapping_is_ignored() -> None:
    doc = import_otm_text('otmVersion: "0.2.0"\nproject: {id: p, name: Odd, attributes: 7}\n')

    assert doc.business_context is None


def test_a_business_context_block_is_restored_when_present() -> None:
    doc = import_otm_text(
        'otmVersion: "0.2.0"\n'
        "project:\n"
        "  id: p\n"
        "  name: Context\n"
        "  attributes:\n"
        "    business_context: {regulatory_context: PCI DSS}\n"
    )

    assert doc.business_context is not None


def test_the_restored_business_context_keeps_its_content() -> None:
    doc = import_otm_text(
        'otmVersion: "0.2.0"\n'
        "project:\n"
        "  id: p\n"
        "  name: Context\n"
        "  attributes:\n"
        "    business_context: {regulatory_context: PCI DSS}\n"
    )

    assert doc.business_context.regulatory_context == "PCI DSS"  # type: ignore[union-attr]


# --------------------------------------------------------------------------- documented scope


def test_analyst_authored_content_is_still_out_of_scope(minimal_doc: ThreatModelDocument) -> None:
    """The bridge converts the architecture; the engine derives threats. Pinned so it stays true."""
    assert set(document_to_otm(minimal_doc)) == {
        "otmVersion",
        "project",
        "trustZones",
        "components",
        "dataflows",
        "assets",
    }
