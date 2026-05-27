"""
Importação assistida a partir de manifests Kubernetes (YAML multi-documento).

Modelo de fluxo simplificado: clientes → Ingress → Service → Deployment (quando nomes coincidem).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from otm_core_schema import Asset, Component, DataFlow, TrustBoundary
from otm_core_schema.enums import AssetKind, ComponentKind, IndustrySector, SystemType

from otm_artifact_import._yamljson import iter_yaml_documents
from otm_artifact_import.ai_import_corpus import build_kubernetes_import_signals_corpus
from otm_artifact_import.builders import assemble_draft, slug_id
from otm_artifact_import.types import ArtifactImportResult, InferenceRecord


def _as_dict(obj: Any) -> dict[str, Any] | None:
    return obj if isinstance(obj, dict) else None


InfFn = Callable[..., None]
# (cid, name, hosts) registered per Ingress for the flow-building phase.
IngressRef = tuple[str, str, list[str]]


def _extract_hosts_from_rules(rules: Any) -> list[str]:
    hosts: list[str] = []
    if isinstance(rules, list):
        for r in rules:
            rd = _as_dict(r)
            if rd and rd.get("host"):
                hosts.append(str(rd["host"]))
    return hosts


def _extract_container_images(pod_spec: dict[str, Any]) -> list[str]:
    cnts = pod_spec.get("containers") or []
    images: list[str] = []
    if isinstance(cnts, list):
        for c in cnts:
            cd = _as_dict(c)
            if cd and cd.get("image"):
                images.append(str(cd["image"]))
    return images


def _handle_ingress(
    name: str, doc: dict[str, Any], filename: str, tb_edge: str,
    components: list[Component], ingresses: list[IngressRef],
) -> None:
    cid = slug_id(f"ing_{name}", prefix="ing")
    hosts = _extract_hosts_from_rules(doc.get("rules") or [])
    ingresses.append((cid, name, hosts))
    components.append(
        Component(
            id=cid,
            name=f"Ingress/{name}",
            kind=ComponentKind.GATEWAY,
            description="Ingress controller (recurso Ingress).",
            technology="Kubernetes Ingress",
            in_trust_boundary=tb_edge,
            metadata={"artifact": filename, "hosts": hosts},
        )
    )


def _handle_service(
    name: str, doc: dict[str, Any], filename: str, tb_cluster: str,
    components: list[Component], services: dict[str, str], inf: InfFn,
) -> None:
    cid = slug_id(f"svc_{name}", prefix="svc")
    services[name] = cid
    st = str(doc.get("spec", {}).get("type") or "ClusterIP")
    components.append(
        Component(
            id=cid,
            name=f"Service/{name}",
            kind=ComponentKind.GATEWAY,
            description=f"Service Kubernetes (type={st}).",
            technology="Kubernetes Service",
            in_trust_boundary=tb_cluster,
            metadata={"artifact": filename, "service_type": st},
        )
    )
    if st == "LoadBalancer":
        inf(
            f"Service `{name}` tipo LoadBalancer — provável exposição externa gerida pelo cloud.",
            "medium",
            related=[cid],
        )


def _handle_deployment(
    name: str, doc: dict[str, Any], filename: str, tb_cluster: str,
    components: list[Component], deployments: dict[str, str],
) -> None:
    cid = slug_id(f"dep_{name}", prefix="dep")
    deployments[name] = cid
    spec_dep = _as_dict(doc.get("spec")) or {}
    tmpl = _as_dict(spec_dep.get("template")) or {}
    pod_spec = _as_dict(tmpl.get("spec")) or {}
    images = _extract_container_images(pod_spec)
    components.append(
        Component(
            id=cid,
            name=f"Deployment/{name}",
            kind=ComponentKind.PROCESS,
            description="Carga de trabalho inferida a partir do Deployment.",
            technology="Kubernetes",
            in_trust_boundary=tb_cluster,
            metadata={"artifact": filename, "container_images": images[:10]},
        )
    )


def _handle_configmap(
    name: str, filename: str, tb_cluster: str, components: list[Component], inf: InfFn
) -> None:
    cid = slug_id(f"cfg_{name}", prefix="cfg")
    components.append(
        Component(
            id=cid,
            name=f"ConfigMap/{name}",
            kind=ComponentKind.DATASTORE,
            description="Configuração não-secreta (sensibilidade depende do conteúdo).",
            technology="Kubernetes ConfigMap",
            in_trust_boundary=tb_cluster,
            metadata={"artifact": filename},
        )
    )
    inf(
        f"ConfigMap `{name}` — dependências configuracionais podem ligar a credenciais noutro manifest (Secret).",
        "low",
        related=[cid],
    )


def _parse_workloads(
    docs: list[Any], filename: str, tb_edge: str, tb_cluster: str,
    components: list[Component], ingresses: list[IngressRef],
    services: dict[str, str], deployments: dict[str, str], inf: InfFn,
) -> None:
    for doc in docs:
        kind = str(doc.get("kind") or "")
        meta = _as_dict(doc.get("metadata")) or {}
        name = str(meta.get("name") or "unnamed")
        if kind == "Ingress":
            _handle_ingress(name, doc, filename, tb_edge, components, ingresses)
        elif kind == "Service":
            _handle_service(name, doc, filename, tb_cluster, components, services, inf)
        elif kind == "Deployment":
            _handle_deployment(name, doc, filename, tb_cluster, components, deployments)
        elif kind == "ConfigMap":
            _handle_configmap(name, filename, tb_cluster, components, inf)


def _find_ingress_spec(docs: list[Any], ing_name: str) -> dict[str, Any] | None:
    for d in docs:
        if str(d.get("kind")) != "Ingress":
            continue
        meta = _as_dict(d.get("metadata")) or {}
        if str(meta.get("name") or "") == ing_name:
            # Ingress rules live under `.spec.rules`, not at the document root.
            return _as_dict(d.get("spec"))
    return None


def _backend_service_name(backend: Any) -> str | None:
    bak = _as_dict(backend)
    if not bak:
        return None
    svc = _as_dict(bak.get("service"))
    if svc and svc.get("name"):
        return str(svc["name"])
    if bak.get("serviceName"):
        return str(bak["serviceName"])
    return None


def _service_names_from_paths(paths: Any) -> list[str]:
    names: list[str] = []
    if not isinstance(paths, list):
        return names
    for p in paths:
        pd = _as_dict(p)
        if not pd:
            continue  # pragma: no cover - defensive guard
        svc_name = _backend_service_name(pd.get("backend"))
        if svc_name:
            names.append(svc_name)
    return names


def _ingress_backend_service_names(spec: dict[str, Any] | None) -> list[str]:
    backend_svcs: list[str] = []
    rules = spec.get("rules") if spec else None
    if not isinstance(rules, list):
        return backend_svcs
    for r in rules:
        rd = _as_dict(r)
        http = _as_dict(rd.get("http")) if rd else {}
        paths = (http or {}).get("paths") if http else None
        backend_svcs.extend(_service_names_from_paths(paths))
    return backend_svcs


def _build_ingress_flows(
    docs: list[Any], ingresses: list[IngressRef], services: dict[str, str],
    filename: str, inf: InfFn, unknowns: list[str],
) -> list[DataFlow]:
    flows: list[DataFlow] = []
    for ing_id, ing_name, hosts in ingresses:
        spec = _find_ingress_spec(docs, ing_name)
        backend_svcs = _ingress_backend_service_names(spec)
        if hosts:
            inf(
                f"Ingress `{ing_name}` com host(s) {', '.join(hosts)} — fronteira externa sugerida.",
                "high",
                related=[ing_id],
            )
        else:
            inf(
                f"Ingress `{ing_name}` sem hosts explícitos no manifest — confirmar controlador e regras.",
                "medium",
                related=[ing_id],
            )
        for svc_name in dict.fromkeys(backend_svcs):
            sid = services.get(svc_name)
            if not sid:
                unknowns.append(f"Ingress referencia Service `{svc_name}` não encontrado neste conjunto de manifests.")
                continue
            flows.append(
                DataFlow(
                    id=slug_id(f"fl_{ing_id}_{sid}", prefix="fl"),
                    name=f"Ingress → {svc_name}",
                    from_component=ing_id,
                    to_component=sid,
                    protocol="HTTP",
                    description="Roteamento inferido a partir de Ingress.spec.rules.",
                    metadata={"artifact": filename},
                )
            )
    return flows


def _build_service_workload_flows(
    services: dict[str, str], deployments: dict[str, str], filename: str, inf: InfFn
) -> list[DataFlow]:
    flows: list[DataFlow] = []
    for svc_name, sid in services.items():
        dep_id = deployments.get(svc_name)
        if not dep_id:
            continue
        flows.append(
            DataFlow(
                id=slug_id(f"fl_{sid}_{dep_id}", prefix="fl"),
                name=f"Service → Deployment ({svc_name})",
                from_component=sid,
                to_component=dep_id,
                protocol="TCP (cluster DNS)",
                description="Ligação heurística quando Service e Deployment partilham o mesmo nome.",
                metadata={"artifact": filename},
            )
        )
        inf(
            f"Fluxo service-to-workload sugerido entre Service e Deployment `{svc_name}` (nome coincidente).",
            "medium",
            related=[sid, dep_id],
        )
    return flows


def _build_ext_ingress_flows(ingresses: list[IngressRef], ext: str, filename: str) -> list[DataFlow]:
    flows: list[DataFlow] = []
    for ing_id, ing_name, _hosts in ingresses:
        flows.append(
            DataFlow(
                id=slug_id(f"fl_ext_{ing_id}", prefix="fl"),
                name=f"Clientes → Ingress {ing_name}",
                from_component=ext,
                to_component=ing_id,
                protocol="HTTPS (assumido)",
                description="Exposição típica via Ingress; confirmar TLS e política.",
                metadata={"artifact": filename},
            )
        )
    return flows


def _build_workload_assets(deployments: dict[str, str], filename: str, inf: InfFn) -> list[Asset]:
    if not deployments:
        return []
    asset = Asset(
        id="asset_workload_images",
        name="Imagens de contentor",
        asset_kind=AssetKind.SERVICE,
        sensitivity="internal",
        description="Inventário parcial de imagens listadas nos Deployments.",
        related_component_ids=list(deployments.values()),
        metadata={"artifact": filename},
    )
    inf(
        "Dependências de implementação (imagens) listadas nos Deployments — cadeia de supply chain não avaliada.",
        "low",
        related=list(deployments.values()),
    )
    return [asset]


def import_kubernetes_text(text: str, *, filename: str = "manifests.yaml") -> ArtifactImportResult:
    inferences: list[InferenceRecord] = []
    unknowns: list[str] = []
    inf_idx = 0

    def inf(msg: str, conf: str, *, related: list[str] | None = None) -> None:
        nonlocal inf_idx
        inf_idx += 1
        inferences.append(
            InferenceRecord(
                id=f"inf_{inf_idx:03d}",
                message=msg,
                confidence=conf,  # type: ignore[arg-type]
                source="kubernetes",
                related_component_ids=list(related or []),
            )
        )

    docs = list(iter_yaml_documents(text))
    if not docs:
        unknowns.append("Nenhum documento YAML válido encontrado.")

    tb_cluster = "tb_k8s_cluster"
    tb_edge = "tb_cluster_edge"

    ext = "ext_k8s_clients"
    components: list[Component] = [
        Component(
            id=ext,
            name="Clientes (fora do cluster)",
            kind=ComponentKind.EXTERNAL_ENTITY,
            description="Utilizadores ou sistemas externos inferidos.",
            in_trust_boundary=tb_edge,
            metadata={"artifact": filename},
        ),
    ]

    ingresses: list[IngressRef] = []
    services: dict[str, str] = {}
    deployments: dict[str, str] = {}

    _parse_workloads(docs, filename, tb_edge, tb_cluster, components, ingresses, services, deployments, inf)

    flows: list[DataFlow] = []
    flows.extend(_build_ingress_flows(docs, ingresses, services, filename, inf, unknowns))
    flows.extend(_build_service_workload_flows(services, deployments, filename, inf))
    flows.extend(_build_ext_ingress_flows(ingresses, ext, filename))

    boundaries: list[TrustBoundary] = [
        TrustBoundary(
            id=tb_edge,
            name="Borda do cluster",
            description="Ingress e clientes externos.",
            member_component_ids=[],
        ),
        TrustBoundary(
            id=tb_cluster,
            name="Interior do cluster",
            description="Services, Deployments e config.",
            member_component_ids=[],
        ),
    ]

    assets: list[Asset] = _build_workload_assets(deployments, filename, inf)

    chart_yaml = "Chart.yaml" in text and "apiVersion:" in text
    if chart_yaml:
        unknowns.append(
            "Conteúdo parece incluir Chart Helm — apenas manifests Kubernetes directos são interpretados aqui."
        )

    if docs and not (ingresses or services or deployments):
        inf(
            "Nenhum Ingress/Service/Deployment reconhecido — apenas outros tipos ou CRDs.",
            "low",
            related=[],
        )

    k8s_docs = [d for d in docs if isinstance(d, dict)]
    import_corpus = build_kubernetes_import_signals_corpus(k8s_docs)
    return assemble_draft(
        title=f"Kubernetes ({filename})",
        summary=f"Rascunho K8s — {len(deployments)} deployment(s), {len(services)} service(s), {len(ingresses)} ingress.",
        source_kind="kubernetes",
        system_type=SystemType.HYBRID,
        industry=IndustrySector.CLOUD_NATIVE,
        components=components,
        data_flows=flows,
        trust_boundaries=boundaries,
        assets=assets,
        inferences=inferences,
        unknowns=unknowns,
        extra_assumptions=[
            "Selectors de Service→Pod não foram avaliados; apenas casos com nomes coincidentes.",
            "Secrets e ServiceAccounts não foram lidos automaticamente.",
        ],
        import_signals_corpus=import_corpus or None,
    )


def import_kubernetes_path(path: Path) -> ArtifactImportResult:
    if path.is_dir():
        chunks: list[str] = []
        for p in sorted(path.glob("*.yml")) + sorted(path.glob("*.yaml")):
            chunks.append(p.read_text(encoding="utf-8"))
        text = "\n---\n".join(chunks)
        res = import_kubernetes_text(text, filename=f"{path.name}/")
        if not chunks:
            res.unknowns.append("Directório sem `.yaml`/`.yml`.")
        return res
    return import_kubernetes_text(path.read_text(encoding="utf-8"), filename=path.name)
