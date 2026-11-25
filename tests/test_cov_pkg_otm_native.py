"""OTM (IriusRisk 0.2.0) bridge — id reconciliation and type mapping.

An OTM file comes from another tool (IriusRisk, StartLeft, a hand-written export), so the
importer cannot assume it is well formed. Two properties matter and neither was covered:

* **A repeated id must not sink the import.** Our canonical schema rejects duplicate entity
  ids outright, so an OTM file that repeats one would fail validation with a message about a
  document the user never wrote. The bridge keeps the first occurrence instead.
* **Two distinct OTM ids must stay distinct.** They are slugged into canonical ids, and the
  slug is lossy ("Order DB" and "order db" collapse). Merging them would silently fuse two
  components into one.
"""

from __future__ import annotations

from otm_artifact_import.otm_native import document_to_otm, import_otm_text

_DUPLICATE_IDS = """
otmVersion: "0.2.0"
project: {id: p, name: Repeated ids}
trustZones:
  - {id: internet, name: Internet}
  - {id: internet, name: Internet (second copy)}
components:
  - {id: api, name: API, type: web-service, parent: {trustZone: internet}}
  - {id: api, name: API (second copy), type: web-service}
dataflows:
  - {id: call, name: first, source: api, destination: api}
  - {id: call, name: second, source: api, destination: api}
assets:
  - {id: pii, name: Customer data}
  - {id: pii, name: Customer data (second copy)}
"""

_KINDS = """
otmVersion: "0.2.0"
project: {id: p, name: Type mapping}
components:
  - {id: bus, name: Event bus, type: kafka-topic}
  - {id: edge, name: Edge, type: waf}
  - {id: alice, name: Alice, type: person}
  - {id: crm, name: CRM, type: third-party}
  - {id: svc, name: Service, type: web-service}
"""


def test_a_repeated_otm_id_keeps_the_first_entry_instead_of_failing_validation() -> None:
    doc = import_otm_text(_DUPLICATE_IDS)

    assert [b.id for b in doc.trust_boundaries] == ["internet"]
    assert [c.id for c in doc.components] == ["api"]
    assert [f.id for f in doc.data_flows] == ["call"]
    assert [a.id for a in doc.assets] == ["pii"]


def test_the_first_entry_is_the_one_kept_not_the_last() -> None:
    """Keeping the first entry has to be observable, otherwise the dedup is untestable policy."""
    doc = import_otm_text(_DUPLICATE_IDS)

    assert doc.components[0].name == "API"
    assert doc.assets[0].name == "Customer data"
    assert doc.trust_boundaries[0].name == "Internet"


def test_two_otm_ids_that_slug_alike_stay_two_components() -> None:
    """`slug_id` is lossy; without the collision counter these would fuse into one component."""
    doc = import_otm_text(
        'otmVersion: "0.2.0"\n'
        "project: {id: p, name: Slug collision}\n"
        "components:\n"
        '  - {id: "Order DB", name: Primary, type: database}\n'
        '  - {id: "order db", name: Replica, type: database}\n'
    )

    assert [c.name for c in doc.components] == ["Primary", "Replica"]
    assert len({c.id for c in doc.components}) == 2


def test_otm_component_types_map_onto_the_canonical_kinds() -> None:
    """OTM `type` is a free string; the bridge has to recognise the common vocabularies."""
    kinds = {c.id: c.kind.value for c in import_otm_text(_KINDS).components}

    assert kinds["bus"] == "queue"
    assert kinds["edge"] == "gateway"
    assert kinds["alice"] == "user"
    assert kinds["crm"] == "external_entity"
    assert kinds["svc"] == "process"


def test_descriptions_survive_the_round_trip_back_to_otm() -> None:
    """The description is the only free-text carrier OTM gives these entities.

    Dropping it on export would quietly strip the reviewer's notes from every model handed to
    an OTM consumer.
    """
    doc = import_otm_text(
        'otmVersion: "0.2.0"\n'
        "project: {id: p, name: Notes}\n"
        "trustZones:\n"
        "  - {id: tz, name: Zone, description: zone note}\n"
        "components:\n"
        "  - {id: api, name: API, type: web-service, description: component note, parent: {trustZone: tz}}\n"
        "dataflows:\n"
        "  - {id: call, name: loop, source: api, destination: api}\n"
        "assets:\n"
        "  - {id: pii, name: Customer data, description: asset note}\n"
    )

    out = document_to_otm(doc)

    assert out["trustZones"][0]["description"] == "zone note"
    assert out["components"][0]["description"] == "component note"
    assert out["assets"][0]["description"] == "asset note"


def test_an_entity_without_a_description_does_not_gain_an_empty_one() -> None:
    out = document_to_otm(import_otm_text(_KINDS))

    assert "description" not in out["components"][0]
    assert "trustZones" not in out
