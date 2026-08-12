"""Open Threat Model (OTM) interoperability — bridge to/from the canonical document.

OTM is IriusRisk's tool-agnostic threat-model exchange standard
(https://github.com/iriusrisk/OpenThreatModel, schema otm-0.2.0). Our canonical
`.otm.yaml` is OTM-*inspired* but distinct (snake_case, `trust_boundaries`,
`in_trust_boundary` refs). This module converts both directions so models can
move between App Suite Modeling and the OTM ecosystem (IriusRisk, StartLeft).

Scope: the structural model — project/metadata, trust zones, components,
dataflows, assets. OTM `threats`/`mitigations` are user-authored content; they
are not re-mapped here (our engine derives threats), but the round-trip of the
architecture is faithful.

Known fidelity limits on export (`document_to_otm`): OTM expresses risk as 0-100
integers while the canonical document uses enums, so asset
`data_classification`/`business_criticality` and trust-boundary trust level are
emitted as the neutral constant 50 rather than translated. Re-importing therefore
restores the architecture, not those risk attributes.
"""

from __future__ import annotations

from typing import Any

from otm_core_schema import (
    Asset,
    Component,
    DataFlow,
    Metadata,
    ModelInfo,
    ThreatModelDocument,
    TrustBoundary,
)
from otm_core_schema.enums import ComponentKind

from otm_artifact_import._yamljson import load_object_from_text
from otm_artifact_import.builders import slug_id

OTM_VERSION = "0.2.0"
_DEFAULT_TRUST_RATING = 50
_DEFAULT_ASSET_RISK = 50


def _entries(otm: dict[str, Any], key: str) -> list[Any]:
    """Read an OTM collection, rejecting a present-but-non-array value.

    Absent/null means "no entries". Anything else must be an array: a truthy scalar
    (`components: 5`) would otherwise raise `TypeError: 'int' object is not iterable`,
    and a string or mapping would silently iterate its characters/keys. Raising here
    (rather than coercing to `[]`) keeps a malformed file from importing as an empty
    model — the caller turns this into a friendly error.
    """
    value = otm.get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"OTM field `{key}` must be an array, got {type(value).__name__}.")
    return value


def _kind_from_otm_type(otm_type: Any) -> ComponentKind:
    """Map an OTM component `type` (free string) to our `ComponentKind`."""
    t = str(otm_type or "").strip().lower()
    try:
        return ComponentKind(t)  # exact match — round-trips our own OTM exports
    except ValueError:
        pass
    if any(k in t for k in ("datastore", "database", "storage", "bucket", "cache", "db", "data-store")):
        return ComponentKind.DATASTORE
    if any(k in t for k in ("queue", "topic", "kafka", "broker", "bus", "message")):
        return ComponentKind.QUEUE
    if any(k in t for k in ("gateway", "proxy", "load-balancer", "load_balancer", "waf", "ingress", "cdn")):
        return ComponentKind.GATEWAY
    if any(k in t for k in ("user", "actor", "person", "customer")):
        return ComponentKind.USER
    if any(k in t for k in ("external", "third-party", "third_party", "client", "browser", "mobile", "saas")):
        return ComponentKind.EXTERNAL_ENTITY
    return ComponentKind.PROCESS


class _IdRemap:
    """Stable, collision-free mapping from OTM ids to canonical entity ids."""

    def __init__(self) -> None:
        self._by_otm: dict[str, str] = {}
        self._owner: dict[str, str] = {}

    def __call__(self, otm_id: Any, *, prefix: str) -> str:
        key = str(otm_id)
        if key in self._by_otm:
            return self._by_otm[key]
        base = slug_id(key, prefix=prefix)
        cid = base
        n = 1
        while cid in self._owner and self._owner[cid] != key:
            n += 1
            cid = f"{base[:52]}_{n}"
        self._by_otm[key] = cid
        self._owner[cid] = key
        return cid


def _otm_parent_trust_zone(parent: Any) -> str | None:
    if isinstance(parent, dict):
        tz = parent.get("trustZone")
        return str(tz) if tz else None
    return None


def _identified_entries(otm: dict[str, Any], key: str) -> list[dict[str, Any]]:
    """Entries of an OTM collection that are mappings carrying an `id`.

    Anything else cannot be remapped onto a canonical entity, so it is skipped here once
    instead of being re-checked by every caller.
    """
    return [e for e in _entries(otm, key) if isinstance(e, dict) and e.get("id") is not None]


def _trust_boundaries_from_otm(otm: dict[str, Any], remap: _IdRemap) -> tuple[list[TrustBoundary], set[str]]:
    boundaries: list[TrustBoundary] = []
    boundary_ids: set[str] = set()
    for tz in _identified_entries(otm, "trustZones"):
        bid = remap(tz["id"], prefix="tz")
        if bid in boundary_ids:
            continue
        boundary_ids.add(bid)
        boundaries.append(
            TrustBoundary(id=bid, name=str(tz.get("name") or tz["id"]), description=tz.get("description"))
        )
    return boundaries, boundary_ids


def _components_from_otm(
    otm: dict[str, Any], remap: _IdRemap, boundary_ids: set[str]
) -> tuple[list[Component], set[str]]:
    components: list[Component] = []
    comp_ids: set[str] = set()
    for c in _identified_entries(otm, "components"):
        cid = remap(c["id"], prefix="comp")
        if cid in comp_ids:
            continue
        tz_id = _otm_parent_trust_zone(c.get("parent"))
        in_tb = remap(tz_id, prefix="tz") if tz_id else None
        if in_tb not in boundary_ids:
            in_tb = None  # keep referential integrity (drop dangling parent)
        comp_ids.add(cid)
        components.append(
            Component(
                id=cid,
                name=str(c.get("name") or c["id"]),
                kind=_kind_from_otm_type(c.get("type")),
                description=c.get("description"),
                in_trust_boundary=in_tb,
            )
        )
    return components, comp_ids


def _data_flows_from_otm(otm: dict[str, Any], remap: _IdRemap, comp_ids: set[str]) -> list[DataFlow]:
    flows: list[DataFlow] = []
    flow_ids: set[str] = set()
    for df in _identified_entries(otm, "dataflows"):
        src = remap(df["source"], prefix="comp") if df.get("source") is not None else None
        dst = remap(df["destination"], prefix="comp") if df.get("destination") is not None else None
        if src not in comp_ids or dst not in comp_ids:
            continue  # skip dataflows referencing unknown components
        fid = remap(df["id"], prefix="fl")
        if fid in flow_ids:
            continue
        flow_ids.add(fid)
        flows.append(
            DataFlow(
                id=fid,
                name=df.get("name"),
                from_component=src,
                to_component=dst,
                description=df.get("description"),
            )
        )
    return flows


def _assets_from_otm(otm: dict[str, Any], remap: _IdRemap) -> list[Asset]:
    assets: list[Asset] = []
    asset_ids: set[str] = set()
    for a in _identified_entries(otm, "assets"):
        aid = remap(a["id"], prefix="asset")
        if aid in asset_ids:
            continue
        asset_ids.add(aid)
        assets.append(Asset(id=aid, name=str(a.get("name") or a["id"]), description=a.get("description")))
    return assets


def otm_to_document(otm: dict[str, Any]) -> ThreatModelDocument:
    """Convert a parsed OTM object into a validated canonical `ThreatModelDocument`."""
    remap = _IdRemap()
    project_raw = otm.get("project")
    project: dict[str, Any] = project_raw if isinstance(project_raw, dict) else {}

    # Call order is load-bearing, not cosmetic: `remap` is stateful, and two OTM ids that slug
    # to the same base are disambiguated with a counter awarded on a first-come basis. Reordering
    # these four lines would silently rename entities across the whole import.
    boundaries, boundary_ids = _trust_boundaries_from_otm(otm, remap)
    components, comp_ids = _components_from_otm(otm, remap, boundary_ids)
    flows = _data_flows_from_otm(otm, remap, comp_ids)
    assets = _assets_from_otm(otm, remap)

    return ThreatModelDocument(
        model_info=ModelInfo(),
        metadata=Metadata(
            title=str(project.get("name") or "Imported OTM model"),
            summary=project.get("description"),
            tags=["imported", "otm"],
        ),
        components=components,
        data_flows=flows,
        trust_boundaries=boundaries,
        assets=assets,
    )


def import_otm_text(text: str) -> ThreatModelDocument:
    """Parse OTM YAML/JSON text and convert to a canonical document.

    The root-is-a-mapping check lives in `load_object_from_text`, which is typed
    `-> dict[str, Any]` and raises for a list, scalar or null root. Repeating it
    here produced an unreachable branch — and a second, differently worded error
    message for a condition a caller could never actually reach.
    """
    return otm_to_document(load_object_from_text(text))


def _project_to_otm(metadata: Metadata) -> dict[str, Any]:
    project: dict[str, Any] = {"id": slug_id(metadata.title, prefix="proj"), "name": metadata.title}
    if metadata.summary:
        project["description"] = metadata.summary
    return project


def _trust_zones_to_otm(boundaries: list[TrustBoundary]) -> list[dict[str, Any]]:
    zones: list[dict[str, Any]] = []
    for tb in boundaries:
        zone: dict[str, Any] = {"id": tb.id, "name": tb.name, "risk": {"trustRating": _DEFAULT_TRUST_RATING}}
        if tb.description:
            zone["description"] = tb.description
        zones.append(zone)
    return zones


def _components_to_otm(components: list[Component]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in components:
        comp: dict[str, Any] = {"id": c.id, "name": c.name, "type": c.kind.value}
        if c.in_trust_boundary:
            comp["parent"] = {"trustZone": c.in_trust_boundary}
        if c.description:
            comp["description"] = c.description
        out.append(comp)
    return out


def _dataflows_to_otm(flows: list[DataFlow]) -> list[dict[str, Any]]:
    return [
        {
            "id": df.id,
            "name": df.name or df.id,
            "source": df.from_component,
            "destination": df.to_component,
            "bidirectional": False,
        }
        for df in flows
    ]


def _assets_to_otm(assets: list[Asset]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for a in assets:
        asset: dict[str, Any] = {
            "id": a.id,
            "name": a.name,
            "risk": {
                "confidentiality": _DEFAULT_ASSET_RISK,
                "integrity": _DEFAULT_ASSET_RISK,
                "availability": _DEFAULT_ASSET_RISK,
            },
        }
        if a.description:
            asset["description"] = a.description
        out.append(asset)
    return out


def document_to_otm(doc: ThreatModelDocument) -> dict[str, Any]:
    """Convert a canonical document into an OTM (0.2.0) object."""
    otm: dict[str, Any] = {"otmVersion": OTM_VERSION, "project": _project_to_otm(doc.metadata)}

    # An empty collection is omitted rather than emitted as `[]` — except `components`, which
    # OTM consumers expect to be present even when the model has none. Key insertion order is
    # the emitted document order, so it follows the OTM 0.2.0 reading order.
    if doc.trust_boundaries:
        otm["trustZones"] = _trust_zones_to_otm(doc.trust_boundaries)
    otm["components"] = _components_to_otm(doc.components)
    if doc.data_flows:
        otm["dataflows"] = _dataflows_to_otm(doc.data_flows)
    if doc.assets:
        otm["assets"] = _assets_to_otm(doc.assets)

    return otm
