"""Regressions — importers must not crash on valid-but-colliding or hostile input.

Each of these inputs previously raised (schema "duplicate id" -> 400/CLI crash,
or AttributeError -> 500). The importers now produce a valid draft, recording a
reconciliation note where entities were merged.
"""

from __future__ import annotations

from otm_artifact_import.k8s_import import import_kubernetes_text
from otm_artifact_import.openapi_import import import_openapi_text
from otm_artifact_import.terraform_import import import_terraform_text


def _ids_unique(result) -> bool:
    ids = [c.id for c in result.document.components]
    return len(ids) == len(set(ids))


def test_kubernetes_same_name_services_across_namespaces_are_preserved() -> None:
    text = """
apiVersion: v1
kind: Service
metadata: {name: api, namespace: ns1}
spec: {type: ClusterIP}
---
apiVersion: v1
kind: Service
metadata: {name: api, namespace: ns2}
spec: {type: ClusterIP}
"""
    result = import_kubernetes_text(text)
    assert _ids_unique(result)
    services = [c for c in result.document.components if c.technology == "Kubernetes Service"]
    assert len(services) == 2
    assert {c.metadata["namespace"] for c in services} == {"ns1", "ns2"}
    assert result.unknowns == []


def test_terraform_duplicate_resource_address_does_not_crash() -> None:
    text = """
resource "aws_s3_bucket" "data" {
  bucket = "a"
}
resource "aws_s3_bucket" "data" {
  bucket = "b"
}
"""
    result = import_terraform_text(text)
    assert _ids_unique(result)


def test_openapi_non_string_method_key_is_ignored() -> None:
    # `on:` is parsed as the YAML 1.1 boolean key True; `get:` is a real op.
    text = """
openapi: 3.0.0
info:
  title: Edge API
  version: "1.0"
paths:
  /x:
    on:
      responses:
        "200": {description: ok}
    get:
      responses:
        "200": {description: ok}
"""
    result = import_openapi_text(text)
    # No crash; the document is a valid draft and the bool key was skipped.
    assert result.document is not None
    assert _ids_unique(result)
