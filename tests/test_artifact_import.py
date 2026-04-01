"""Testes da importação assistida — rascunho canónico, inferências e tolerância a entradas fracas."""

from __future__ import annotations

from otm_artifact_import import (
    import_kubernetes_text,
    import_openapi_text,
    import_terraform_text,
)
from otm_core_schema import load_document_from_dict

_MINIMAL_OPENAPI = """
openapi: 3.0.0
info:
  title: Payments API
  version: 1.0.0
servers:
  - url: https://api.example.com
paths:
  /pay:
    post:
      operationId: createPayment
      security:
        - bearer: []
components:
  securitySchemes:
    bearer:
      type: http
      scheme: bearer
"""

_OPENAPI_PARTIAL = """
openapi: 3.0.0
info:
  title: Broken
  version: "1"
"""

_TERRAFORM = """
resource "aws_s3_bucket" "logs" {
  bucket = "my-logs"
}
resource "aws_db_instance" "primary" {
  engine = "postgres"
}
resource "aws_security_group" "wide" {
  ingress {
    cidr_blocks = ["0.0.0.0/0"]
  }
}
"""

_K8S = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: api
spec:
  rules:
  - host: api.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: api
            port:
              number: 80
---
apiVersion: v1
kind: Service
metadata:
  name: api
spec:
  type: ClusterIP
  selector:
    app: api
  ports:
  - port: 80
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 2
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
        image: example/api:1.2.3
"""


def test_openapi_basic_draft_valid() -> None:
    result = import_openapi_text(_MINIMAL_OPENAPI, filename="t.yaml")
    d = result.document.model_dump(mode="json", by_alias=True)
    doc = load_document_from_dict(d)
    assert doc.metadata.title.endswith("OpenAPI)")
    ids = {c.id for c in doc.components}
    assert "ext_http_clients" in ids
    assert doc.data_flows
    assert any(i.source == "openapi" for i in result.inferences)
    assert any("operação" in i.message.lower() or "http" in i.message.lower() for i in result.inferences)
    assert len(result.explanations) == len(result.inferences)
    assert result.explanations[0].type.value == "import_inference"


def test_openapi_partial_still_stable() -> None:
    result = import_openapi_text(_OPENAPI_PARTIAL, filename="partial.yaml")
    load_document_from_dict(result.document.model_dump(mode="json", by_alias=True))
    assert result.unknowns
    assert any(i.confidence == "low" or i.confidence == "medium" for i in result.inferences)


def test_terraform_basic_and_public_hint() -> None:
    result = import_terraform_text(_TERRAFORM, filename="infra.tf")
    doc = load_document_from_dict(result.document.model_dump(mode="json", by_alias=True))
    kinds = {c.kind.value for c in doc.components}
    assert "datastore" in kinds or "process" in kinds or "other" in kinds
    assert any("0.0.0.0/0" in i.message or "rede" in i.message.lower() for i in result.inferences)
    assert result.inferences


def test_kubernetes_flows_and_explainability() -> None:
    result = import_kubernetes_text(_K8S, filename="k8s.yaml")
    doc = load_document_from_dict(result.document.model_dump(mode="json", by_alias=True))
    assert len(doc.data_flows) >= 2
    assert any("ingress" in i.message.lower() for i in result.inferences)
    assert all(i.id.startswith("inf_") for i in result.inferences)
    bc = doc.business_context
    assert bc is not None
    assert bc.assumptions


def test_inference_records_have_confidence() -> None:
    r = import_openapi_text(_MINIMAL_OPENAPI)
    for i in r.inferences:
        assert i.confidence in ("low", "medium", "high")
        assert i.message
        assert i.source == "openapi"
