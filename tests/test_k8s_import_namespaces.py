"""Kubernetes resource identity and flow resolution across namespaces."""

from typing import Any

import yaml
from otm_artifact_import.k8s_import import import_kubernetes_text
from otm_artifact_import.types import ArtifactImportResult


def _resource(kind: str, name: str, namespace: str, **spec: Any) -> dict[str, Any]:
    return {"kind": kind, "metadata": {"name": name, "namespace": namespace}, "spec": spec}


def _stack(namespace: str, backend: str) -> list[dict[str, Any]]:
    return [
        _resource("Ingress", "catalog", namespace, defaultBackend={"service": {"name": backend}}),
        _resource("Service", "catalog", namespace),
        _resource("Deployment", "catalog", namespace),
        _resource("ConfigMap", "catalog", namespace),
    ]


def _import(docs: list[dict[str, Any]], *, filename: str = "manifests.yaml") -> ArtifactImportResult:
    return import_kubernetes_text(yaml.safe_dump_all(docs), filename=filename)


def test_same_named_resources_and_flows_stay_in_their_namespace() -> None:
    docs = _stack("storefront", "catalog") + _stack("internal", "private")
    docs.append(_resource("Service", "private", "internal"))
    result = _import(docs)
    doc = result.document
    ids = {c.name: c.id for c in doc.components if c.id != "ext_k8s_clients"}
    assert len(ids) == 9
    assert len(set(ids.values())) == 9
    assert {c.metadata["namespace"] for c in doc.components if c.id in ids.values()} == {"storefront", "internal"}
    edges = {(f.from_component, f.to_component) for f in doc.data_flows}
    assert edges == {
        ("ext_k8s_clients", ids["Ingress/storefront/catalog"]),
        ("ext_k8s_clients", ids["Ingress/internal/catalog"]),
        (ids["Ingress/storefront/catalog"], ids["Service/storefront/catalog"]),
        (ids["Ingress/internal/catalog"], ids["Service/internal/private"]),
        (ids["Service/storefront/catalog"], ids["Deployment/storefront/catalog"]),
        (ids["Service/internal/catalog"], ids["Deployment/internal/catalog"]),
    }
    assert set(doc.assets[0].related_component_ids) == {
        ids["Deployment/storefront/catalog"],
        ids["Deployment/internal/catalog"],
    }
    assert result.unknowns == []


def test_ids_survive_order_file_and_resource_set_changes() -> None:
    original = _stack("storefront", "catalog")
    revised = original + _stack("internal", "catalog")
    alone = _import(original).document
    combined = _import(revised).document
    reordered = _import(revised[::-1], filename="reordered.yaml").document
    assert {c.id for c in alone.components} < {c.id for c in combined.components}
    assert {f.id for f in alone.data_flows} < {f.id for f in combined.data_flows}
    assert {c.name: c.id for c in combined.components} == {c.name: c.id for c in reordered.components}
    assert {(f.from_component, f.to_component): f.id for f in combined.data_flows} == {
        (f.from_component, f.to_component): f.id for f in reordered.data_flows
    }


def test_missing_local_resources_are_not_linked_across_namespaces() -> None:
    result = _import(
        [
            _resource("Ingress", "catalog", "internal", defaultBackend={"service": {"name": "catalog"}}),
            _resource("Service", "catalog", "storefront"),
            _resource("Deployment", "catalog", "internal"),
        ]
    )
    assert len(result.document.data_flows) == 1
    assert result.document.data_flows[0].from_component == "ext_k8s_clients"
    assert any("catalog" in note and "internal" in note for note in result.unknowns)


def test_default_namespace_keeps_short_legacy_ids() -> None:
    explicit = _stack("default", "catalog")
    implicit = _stack("default", "catalog")
    for doc in implicit:
        del doc["metadata"]["namespace"]

    doc = _import(explicit).document
    other = _import(implicit).document
    assert [c.id for c in doc.components] == [
        "ext_k8s_clients",
        "ing_catalog",
        "svc_catalog",
        "dep_catalog",
        "cfg_catalog",
    ]
    assert [c.id for c in doc.components] == [c.id for c in other.components]
    expected_flows = {
        "fl_ing_catalog_svc_catalog",
        "fl_svc_catalog_dep_catalog",
        "fl_ext_ing_catalog",
    }
    assert {f.id for f in doc.data_flows} == expected_flows
    assert {f.id for f in other.data_flows} == expected_flows


def test_long_identifiers_keep_distinct_components_and_flows() -> None:
    names = ["a" * 55 + "-east", "a" * 55 + "-west"]
    docs = [
        resource
        for name in names
        for resource in (
            _resource("Ingress", name, "default", defaultBackend={"service": {"name": name}}),
            _resource("Service", name, "default"),
            _resource("Deployment", name, "default"),
        )
    ]
    first = _import(docs).document
    reordered = _import(docs[::-1]).document
    assert len(first.components) == 7
    assert len(first.data_flows) == 6
    assert {c.name: c.id for c in first.components} == {c.name: c.id for c in reordered.components}
    assert {f.id for f in first.data_flows} == {f.id for f in reordered.data_flows}
