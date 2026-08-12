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

How the architecture attributes survive: OTM 0.2.0 gives every entity a free-form
``attributes`` object (see ``otm_schema.json``; the schema does not forbid it and
does not constrain its contents). Everything the canonical document carries that
OTM has no dedicated slot for — a flow's ``protocol``/``authenticated``/``encrypted``,
a component's ``technology``, an asset's ``data_classification`` — is written there
under its canonical field name, so a third-party OTM consumer can read it and a
re-import restores it exactly. Component↔asset links use OTM's own slot,
``component.assets.processed`` / ``.stored``; the canonical ``model`` header and
``business_context`` travel in ``project.attributes``.

Known fidelity limits on export (`document_to_otm`): OTM expresses risk as 0-100
numbers. Asset ``data_classification``/``business_criticality`` are *projected*
onto that scale (see ``_ASSET_CONFIDENTIALITY`` / ``_ASSET_INTEGRITY``) so an OTM
consumer sees the user's classification instead of a constant, and the exact enum
travels in ``attributes`` for a lossless round trip. Trust-boundary ``trust_level``
is free text with no ordinal meaning, so ``trustRating`` stays at the neutral
constant and the text travels in ``attributes``.

What the bridge still does **not** carry, by design: ``threats``, ``mitigations``
and ``evidence_suggestions`` (analyst-authored content — our engine derives its
own), ``residual_risk_summary``, ``import_signals_corpus`` (import-derived text,
not architecture), and document ``metadata`` beyond title/summary — an imported
model is re-tagged ``imported``/``otm`` on purpose. `tests/test_p2_export_otm_bridge.py`
pins that list so it cannot grow silently.
"""

from __future__ import annotations

from functools import cache
from typing import Any

from otm_core_schema import (
    Asset,
    BusinessContext,
    Component,
    DataFlow,
    Metadata,
    ModelInfo,
    ThreatModelDocument,
    TrustBoundary,
)
from otm_core_schema.enums import ComponentKind, CriticalityLevel, DataClassificationLevel
from pydantic import BaseModel, TypeAdapter, ValidationError

from otm_artifact_import._yamljson import load_object_from_text
from otm_artifact_import.builders import slug_id

OTM_VERSION = "0.2.0"
_DEFAULT_TRUST_RATING = 50
_DEFAULT_ASSET_RISK = 50

#: Campos que já têm posição própria no OTM — nunca vão para o saco `attributes`, e um
#: `attributes` de outra ferramenta nunca os pode sobrepor (id, origem e destino incluídos:
#: sobrepô-los partia a integridade referencial do documento importado).
_COMPONENT_OTM_SLOTS = frozenset({"id", "name", "kind", "description", "in_trust_boundary", "asset_ids"})
_DATAFLOW_OTM_SLOTS = frozenset({"id", "name", "from_component", "to_component", "description"})
_ASSET_OTM_SLOTS = frozenset({"id", "name", "description"})
_TRUST_BOUNDARY_OTM_SLOTS = frozenset({"id", "name", "description"})

#: Projecção ordinal dos enums canónicos na escala 0-100 do OTM. É uma apresentação para
#: consumidores OTM, não a fonte da verdade: o enum exacto viaja em `attributes` e é ele que o
#: re-import lê. Ainda assim é muito melhor do que a constante 50 que estava aqui antes, que
#: dava o mesmo número ao ativo marcado `restricted` e ao ativo sem classificação nenhuma.
#: Um ativo sem classificação simplesmente não é chave — daí o `| None` no tipo e o neutro 50
#: como default da procura.
_ASSET_CONFIDENTIALITY: dict[DataClassificationLevel | None, int] = {
    DataClassificationLevel.PUBLIC: 10,
    DataClassificationLevel.INTERNAL: 40,
    DataClassificationLevel.CONFIDENTIAL: 70,
    DataClassificationLevel.RESTRICTED: 100,
}
_ASSET_INTEGRITY: dict[CriticalityLevel | None, int] = {
    CriticalityLevel.LOW: 25,
    CriticalityLevel.MEDIUM: 50,
    CriticalityLevel.HIGH: 75,
    CriticalityLevel.CRITICAL: 100,
}


@cache
def _field_adapter(model: type[BaseModel], field: str) -> TypeAdapter[Any]:
    """Validador para um único campo canónico — usado para filtrar `attributes` de terceiros."""
    return TypeAdapter(model.model_fields[field].annotation)


def _attributes_to_otm(entity: BaseModel, slots: frozenset[str]) -> dict[str, Any]:
    """Campos canónicos sem posição própria no OTM, prontos para `attributes`.

    `exclude_defaults` mantém o ficheiro OTM legível: só sai o que o modelador definiu, e o
    re-import reconstrói o resto a partir dos mesmos defaults. Genérico de propósito — um campo
    canónico novo passa a viajar sem tocar aqui.
    """
    data = entity.model_dump(mode="json", exclude_none=True, exclude_defaults=True)
    return {k: v for k, v in data.items() if k not in slots}


def _canonical_fields(raw: Any, model: type[BaseModel], slots: frozenset[str]) -> dict[str, Any]:
    """Filtra um mapa livre, aceitando só chaves canónicas de `model` com o tipo certo.

    `attributes` é um saco livre que outras ferramentas (IriusRisk, StartLeft) também usam, por
    isso um valor estranho não pode rebentar o import: descarta-se essa chave e mantém-se o
    resto, em vez de recusar o ficheiro inteiro ou perder tudo o que vinha ao lado.
    """
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if key in slots or key not in model.model_fields:
            continue
        try:
            out[key] = _field_adapter(model, key).validate_python(value)
        except ValidationError:
            continue
    return out


def _attributes_from_otm(entry: dict[str, Any], model: type[BaseModel], slots: frozenset[str]) -> dict[str, Any]:
    """Campos canónicos recuperados do `attributes` de uma entidade OTM."""
    return _canonical_fields(entry.get("attributes"), model, slots)


def _with_attributes(entry: dict[str, Any], attributes: dict[str, Any]) -> dict[str, Any]:
    """Acrescenta `attributes` só quando há alguma coisa para lá pôr."""
    if attributes:
        entry["attributes"] = attributes
    return entry


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

    def known(self, otm_id: Any) -> str | None:
        """Canonical id for an OTM id already seen, or None — never allocates a new one.

        Reference lists are resolved after every entity exists, and a reference the file never
        defines must be dropped, not turned into a fresh id that points at nothing.
        """
        return self._by_otm.get(str(otm_id))


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
            TrustBoundary(
                id=bid,
                name=str(tz.get("name") or tz["id"]),
                description=tz.get("description"),
                **_attributes_from_otm(tz, TrustBoundary, _TRUST_BOUNDARY_OTM_SLOTS),
            )
        )
    return boundaries, boundary_ids


def _otm_component_asset_refs(entry: dict[str, Any]) -> list[str]:
    """OTM ids in `component.assets.processed` / `.stored`, in order and without repeats.

    OTM splits the link in two; the canonical document has a single `asset_ids`, so the union is
    what round-trips exactly. Ids are still raw OTM ids here — `_resolve_reference_lists` maps
    them onto canonical ids once every entity exists.
    """
    block = entry.get("assets")
    if not isinstance(block, dict):
        return []
    refs: list[str] = []
    for key in ("processed", "stored"):
        value = block.get(key)
        if isinstance(value, list):
            refs.extend(str(v) for v in value)
    return list(dict.fromkeys(refs))


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
                asset_ids=_otm_component_asset_refs(c),
                **_attributes_from_otm(c, Component, _COMPONENT_OTM_SLOTS),
            )
        )
    return components, comp_ids


def _otm_flow_label(entry: dict[str, Any]) -> Any:
    """Etiqueta humana do fluxo, ou None quando o OTM só repetiu o id.

    `dataflows[].name` é obrigatório no OTM e o canónico deixa-o opcional, por isso o export
    preenche-o com o id quando o fluxo não tem nome. Sem esta leitura, o round-trip devolvia
    fluxos baptizados `to_db` — um nome que ninguém escreveu.
    """
    name = entry.get("name")
    return None if name is not None and str(name) == str(entry["id"]) else name


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
                name=_otm_flow_label(df),
                from_component=src,
                to_component=dst,
                description=df.get("description"),
                **_attributes_from_otm(df, DataFlow, _DATAFLOW_OTM_SLOTS),
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
        assets.append(
            Asset(
                id=aid,
                name=str(a.get("name") or a["id"]),
                description=a.get("description"),
                **_attributes_from_otm(a, Asset, _ASSET_OTM_SLOTS),
            )
        )
    return assets


#: Campo de referência -> prefixo com que os seus ids foram remapeados. Os valores que chegam em
#: `attributes` (ou em `component.assets`) são ids OTM; sem esta passagem apontariam para nomes
#: que o documento canónico não tem e a validação do documento recusaria o import inteiro.
_REFERENCE_FIELDS: dict[str, str] = {
    "asset_ids": "asset",
    "related_component_ids": "comp",
    "related_data_flow_ids": "fl",
    "member_component_ids": "comp",
    "outside_component_ids": "comp",
    "crossing_flow_ids": "fl",
}


def _resolve_reference_lists(entities: list[Any], remap: _IdRemap, valid_ids: dict[str, set[str]]) -> None:
    """Traduz as listas de ids para o espaço canónico e descarta o que o ficheiro não define.

    Corre depois de todas as entidades existirem, porque uma fronteira pode referir um componente
    que só aparece mais abaixo no ficheiro. Uma referência pendente é removida em silêncio — é o
    mesmo critério que o importador já usa para um `parent` inexistente ou um dataflow com ponta
    solta: manter o documento válido em vez de rejeitar o ficheiro de outra ferramenta.
    """
    for entity in entities:
        for field, prefix in _REFERENCE_FIELDS.items():
            current = getattr(entity, field, None)
            if not current:
                continue
            allowed = valid_ids[prefix]
            resolved = (remap.known(ref) for ref in current)
            setattr(entity, field, [r for r in resolved if r is not None and r in allowed])


def _project_header(project: dict[str, Any], key: str) -> Any:
    """Bloco de cabeçalho canónico (`model`, `business_context`) guardado em `project.attributes`."""
    attributes = project.get("attributes")
    return attributes.get(key) if isinstance(attributes, dict) else None


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

    valid_ids = {"comp": comp_ids, "fl": {f.id for f in flows}, "asset": {a.id for a in assets}}
    _resolve_reference_lists([*boundaries, *components, *assets], remap, valid_ids)

    model_info = _canonical_fields(_project_header(project, "model"), ModelInfo, frozenset())
    business_context = _canonical_fields(_project_header(project, "business_context"), BusinessContext, frozenset())
    return ThreatModelDocument(
        model_info=ModelInfo(**model_info),
        metadata=Metadata(
            title=str(project.get("name") or "Imported OTM model"),
            summary=project.get("description"),
            tags=["imported", "otm"],
        ),
        business_context=BusinessContext(**business_context) if business_context else None,
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


def _project_to_otm(doc: ThreatModelDocument) -> dict[str, Any]:
    """`project`, com o cabeçalho canónico em `attributes`.

    `model` decide como o motor lê o documento — a metodologia, o tipo de sistema, o setor, o
    perfil semântico do template. Emitir defaults em vez destes valores fazia o modelo
    re-importado ser analisado por outras regras: um modelo `plot4ai` voltava como `stride` e
    perdia as heurísticas de IA todas, em silêncio.
    """
    metadata = doc.metadata
    project: dict[str, Any] = {"id": slug_id(metadata.title, prefix="proj"), "name": metadata.title}
    if metadata.summary:
        project["description"] = metadata.summary
    header: dict[str, Any] = {}
    model = _attributes_to_otm(doc.model_info, frozenset())
    if model:
        header["model"] = model
    if doc.business_context:
        business_context = _attributes_to_otm(doc.business_context, frozenset())
        if business_context:
            header["business_context"] = business_context
    return _with_attributes(project, header)


def _trust_zones_to_otm(boundaries: list[TrustBoundary]) -> list[dict[str, Any]]:
    zones: list[dict[str, Any]] = []
    for tb in boundaries:
        zone: dict[str, Any] = {"id": tb.id, "name": tb.name, "risk": {"trustRating": _DEFAULT_TRUST_RATING}}
        if tb.description:
            zone["description"] = tb.description
        zones.append(_with_attributes(zone, _attributes_to_otm(tb, _TRUST_BOUNDARY_OTM_SLOTS)))
    return zones


def _component_assets_to_otm(component: Component) -> dict[str, list[str]]:
    """Liga o componente aos ativos na posição própria do OTM (`assets.processed` / `.stored`).

    O canónico tem um único `asset_ids` e o OTM pede a divisão; um datastore *armazena* e tudo o
    resto *processa* é a leitura defensável, e a união devolve o conjunto original no re-import.
    """
    if not component.asset_ids:
        return {}
    key = "stored" if component.kind is ComponentKind.DATASTORE else "processed"
    return {key: list(component.asset_ids)}


def _components_to_otm(components: list[Component]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for c in components:
        comp: dict[str, Any] = {"id": c.id, "name": c.name, "type": c.kind.value}
        if c.in_trust_boundary:
            comp["parent"] = {"trustZone": c.in_trust_boundary}
        if c.description:
            comp["description"] = c.description
        linked = _component_assets_to_otm(c)
        if linked:
            comp["assets"] = linked
        out.append(_with_attributes(comp, _attributes_to_otm(c, _COMPONENT_OTM_SLOTS)))
    return out


def _dataflows_to_otm(flows: list[DataFlow]) -> list[dict[str, Any]]:
    return [
        _with_attributes(
            {
                "id": df.id,
                "name": df.name or df.id,
                "source": df.from_component,
                "destination": df.to_component,
                "bidirectional": False,
            },
            _attributes_to_otm(df, _DATAFLOW_OTM_SLOTS),
        )
        for df in flows
    ]


def _asset_risk_to_otm(asset: Asset) -> dict[str, float]:
    """Projecta a classificação do ativo na escala 0-100 do OTM.

    Antes escrevia-se a constante 50 nos três eixos, o que dava ao ativo marcado `restricted` /
    `critical` exactamente o mesmo número que a um ativo sem classificação nenhuma — não era uma
    omissão, era um valor inventado. Sem classificação mantém-se o neutro 50, que é honesto.
    """
    confidentiality = _ASSET_CONFIDENTIALITY.get(asset.data_classification, _DEFAULT_ASSET_RISK)
    integrity = _ASSET_INTEGRITY.get(asset.business_criticality, _DEFAULT_ASSET_RISK)
    return {"confidentiality": confidentiality, "integrity": integrity, "availability": integrity}


def _assets_to_otm(assets: list[Asset]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for a in assets:
        asset: dict[str, Any] = {"id": a.id, "name": a.name, "risk": _asset_risk_to_otm(a)}
        if a.description:
            asset["description"] = a.description
        out.append(_with_attributes(asset, _attributes_to_otm(a, _ASSET_OTM_SLOTS)))
    return out


def document_to_otm(doc: ThreatModelDocument) -> dict[str, Any]:
    """Convert a canonical document into an OTM (0.2.0) object."""
    otm: dict[str, Any] = {"otmVersion": OTM_VERSION, "project": _project_to_otm(doc)}

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
