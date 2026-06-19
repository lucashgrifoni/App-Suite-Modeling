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


def otm_to_document(otm: dict[str, Any]) -> ThreatModelDocument:
    """Convert a parsed OTM object into a validated canonical `ThreatModelDocument`."""
    remap = _IdRemap()
    project_raw = otm.get("project")
    project: dict[str, Any] = project_raw if isinstance(project_raw, dict) else {}
    title = str(project.get("name") or "Imported OTM model")
    summary = project.get("description")

    boundaries: list[TrustBoundary] = []
    boundary_ids: set[str] = set()
    for tz in otm.get("trustZones") or []:
        if not isinstance(tz, dict) or tz.get("id") is None:
            continue
        bid = remap(tz["id"], prefix="tz")
        if bid in boundary_ids:
            continue
        boundary_ids.add(bid)
        boundaries.append(
            TrustBoundary(id=bid, name=str(tz.get("name") or tz["id"]), description=tz.get("description"))
        )

    components: list[Component] = []
    comp_ids: set[str] = set()
    for c in otm.get("components") or []:
        if not isinstance(c, dict) or c.get("id") is None:
            continue
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

    flows: list[DataFlow] = []
    flow_ids: set[str] = set()
    for df in otm.get("dataflows") or []:
        if not isinstance(df, dict) or df.get("id") is None:
            continue
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

    assets: list[Asset] = []
    asset_ids: set[str] = set()
    for a in otm.get("assets") or []:
        if not isinstance(a, dict) or a.get("id") is None:
            continue
        aid = remap(a["id"], prefix="asset")
        if aid in asset_ids:
            continue
        asset_ids.add(aid)
        assets.append(Asset(id=aid, name=str(a.get("name") or a["id"]), description=a.get("description")))

    return ThreatModelDocument(
        model_info=ModelInfo(),
        metadata=Metadata(title=title, summary=summary, tags=["imported", "otm"]),
        components=components,
        data_flows=flows,
        trust_boundaries=boundaries,
        assets=assets,
    )


def import_otm_text(text: str) -> ThreatModelDocument:
    """Parse OTM YAML/JSON text and convert to a canonical document."""
    obj = load_object_from_text(text)
    if not isinstance(obj, dict):
        raise ValueError("OTM root must be a mapping (object).")
    return otm_to_document(obj)


def document_to_otm(doc: ThreatModelDocument) -> dict[str, Any]:
    """Convert a canonical document into an OTM (0.2.0) object."""
    project: dict[str, Any] = {"id": slug_id(doc.metadata.title, prefix="proj"), "name": doc.metadata.title}
    if doc.metadata.summary:
        project["description"] = doc.metadata.summary

    otm: dict[str, Any] = {"otmVersion": OTM_VERSION, "project": project}

    if doc.trust_boundaries:
        zones: list[dict[str, Any]] = []
        for tb in doc.trust_boundaries:
            zone: dict[str, Any] = {"id": tb.id, "name": tb.name, "risk": {"trustRating": _DEFAULT_TRUST_RATING}}
            if tb.description:
                zone["description"] = tb.description
            zones.append(zone)
        otm["trustZones"] = zones

    components: list[dict[str, Any]] = []
    for c in doc.components:
        comp: dict[str, Any] = {"id": c.id, "name": c.name, "type": c.kind.value}
        if c.in_trust_boundary:
            comp["parent"] = {"trustZone": c.in_trust_boundary}
        if c.description:
            comp["description"] = c.description
        components.append(comp)
    otm["components"] = components

    if doc.data_flows:
        otm["dataflows"] = [
            {
                "id": df.id,
                "name": df.name or df.id,
                "source": df.from_component,
                "destination": df.to_component,
                "bidirectional": False,
            }
            for df in doc.data_flows
        ]

    if doc.assets:
        assets: list[dict[str, Any]] = []
        for a in doc.assets:
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
            assets.append(asset)
        otm["assets"] = assets

    return otm
