"""
Preenche `assets: []` nos templates industry com 3 ativos plausíveis e liga datastores.

Uso (na raiz do repositório):
  python scripts/fill_industry_template_assets.py

Reescreve cada ficheiro via `dump_document_to_yaml` após validação Pydantic.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import yaml
from otm_core_schema import dump_document_to_yaml, load_document_from_dict
from otm_core_schema.document import Asset, Component, ThreatModelDocument

TEMPLATES_DIR = _ROOT / "packages" / "industry-packs" / "otm_industry_packs" / "data" / "templates"


def _flows_touching(flows: list, cid: str) -> list[str]:
    out: list[str] = []
    for f in flows:
        fid = f.get("id")
        if not fid:
            continue
        if f.get("from_component") == cid or f.get("to_component") == cid:
            out.append(fid)
    return out


def _stem_prefix(stem: str) -> str:
    return stem.replace("-", "_").replace(".", "_")


def build_three_assets(
    stem: str, components: list[dict], flows: list[dict]
) -> tuple[list[Asset], dict[str, list[str]]]:
    """Gera 3 ativos e mapa component_id -> asset_ids a acrescentar em `asset_ids`."""
    prefix = _stem_prefix(stem)
    comp_ids = [c["id"] for c in components]
    by_kind: dict[str, list[str]] = {}
    for c in components:
        k = str(c.get("kind", "process"))
        by_kind.setdefault(k, []).append(c["id"])

    datastores = by_kind.get("datastore", [])
    processes = by_kind.get("process", [])
    gateways = by_kind.get("gateway", [])
    users = by_kind.get("user", [])
    external = by_kind.get("external_entity", [])

    attach: dict[str, list[str]] = {}
    assets: list[Asset] = []

    # 1 — Dados persistidos ou estado crítico
    if datastores:
        ds = datastores[0]
        rel_flows = _flows_touching(flows, ds)[:5]
        proc_in = None
        for f in flows:
            if f.get("to_component") == ds:
                proc_in = f.get("from_component")
                break
        rel_comps = [c for c in [proc_in, ds] if c]
        if not rel_comps:
            rel_comps = [ds]
        aid = f"{prefix}_persisted_data"
        assets.append(
            Asset(
                id=aid,
                name="Dados persistidos do serviço",
                asset_kind="order_record",
                data_classification="confidential",
                business_criticality="high",
                related_component_ids=rel_comps[:4],
                related_data_flow_ids=rel_flows,
            )
        )
        attach.setdefault(ds, []).append(aid)
    elif processes:
        p0 = processes[0]
        aid = f"{prefix}_application_state"
        assets.append(
            Asset(
                id=aid,
                name="Estado e dados processados pela aplicação",
                asset_kind="session",
                sensitivity="confidential",
                business_criticality="high",
                related_component_ids=[p0],
                related_data_flow_ids=_flows_touching(flows, p0)[:5],
            )
        )
        attach.setdefault(p0, []).append(aid)

    # 2 — Credenciais / segredo operacional
    hub = gateways[0] if gateways else (processes[0] if processes else None)
    if hub and len(assets) < 3:
        aid = f"{prefix}_credentials_and_secrets"
        rel_comps = [hub]
        if processes and processes[0] != hub:
            rel_comps.append(processes[0])
        assets.append(
            Asset(
                id=aid,
                name="Credenciais, chaves e segredos operacionais",
                asset_kind="credential",
                sensitivity="confidential",
                business_criticality="high",
                related_component_ids=rel_comps[:4],
                related_data_flow_ids=_flows_touching(flows, hub)[:5],
            )
        )
        for c in rel_comps[:2]:
            attach.setdefault(c, []).append(aid)

    # 3 — Superfície / integração / auditoria
    third = None
    if len(datastores) > 1:
        third = datastores[1]
    elif external:
        third = external[0]
    elif len(processes) > 1:
        third = processes[-1]
    elif users:
        third = users[0]

    if third is not None and len(assets) < 3:
        aid = f"{prefix}_operational_surface"
        assets.append(
            Asset(
                id=aid,
                name="Superfície operacional e integrações",
                asset_kind="service",
                business_criticality="medium",
                related_component_ids=[third],
                related_data_flow_ids=_flows_touching(flows, third)[:5],
            )
        )
        attach.setdefault(third, []).append(aid)

    # Garantir exatamente 3 ativos quando possível
    while len(assets) < 3 and comp_ids:
        filler_id = comp_ids[min(len(assets), len(comp_ids) - 1)]
        aid = f"{prefix}_asset_{len(assets)}"
        if any(a.id == aid for a in assets):
            break
        assets.append(
            Asset(
                id=aid,
                name="Ativo de contexto do modelo",
                asset_kind="other",
                business_criticality="low",
                related_component_ids=[filler_id],
                related_data_flow_ids=_flows_touching(flows, filler_id)[:3],
            )
        )
        attach.setdefault(filler_id, []).append(aid)

    # Dedupe
    for k, v in list(attach.items()):
        attach[k] = list(dict.fromkeys(v))

    return assets, attach


def merge_component_asset_ids(components: list[Component], attach: dict[str, list[str]]) -> list[Component]:
    out: list[Component] = []
    for c in components:
        extra = attach.get(c.id, [])
        if not extra:
            out.append(c)
            continue
        merged = list(dict.fromkeys((c.asset_ids or []) + extra))
        out.append(c.model_copy(update={"asset_ids": merged}))
    return out


def process_file(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        return False
    assets_raw = data.get("assets")
    if assets_raw not in (None, []) and len(assets_raw) > 0:
        return False

    comps_raw = data.get("components") or []
    flows_raw = data.get("data_flows") or []
    new_assets, attach = build_three_assets(path.stem, comps_raw, flows_raw)
    if not new_assets:
        return False

    doc = load_document_from_dict(data)
    assert isinstance(doc, ThreatModelDocument)
    merged_components = merge_component_asset_ids(doc.components, attach)
    doc = doc.model_copy(update={"assets": new_assets, "components": merged_components})
    # Valida referências cruzadas
    ThreatModelDocument.model_validate(doc.model_dump(mode="json", exclude_none=True))

    path.write_text(dump_document_to_yaml(doc), encoding="utf-8")
    return True


def main() -> None:
    n = 0
    for p in sorted(TEMPLATES_DIR.glob("*.yaml")):
        if process_file(p):
            print(f"updated: {p.name}")
            n += 1
    print(f"Total atualizados: {n}")


if __name__ == "__main__":
    main()
