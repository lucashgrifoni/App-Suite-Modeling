"""Coverage — artifact importers (openapi/k8s/terraform/repo) across varied inputs and edges."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from otm_artifact_import import (
    import_helm_text,
    import_kubernetes_text,
    import_openapi_text,
    import_terraform_text,
    scan_node_express_repo,
)
from otm_artifact_import.helm_import import import_helm_path
from otm_artifact_import.k8s_import import import_kubernetes_path
from otm_artifact_import.terraform_import import import_terraform_path

# --- OpenAPI variety ---

_OPENAPI_RICH = """
openapi: 3.0.1
info: {title: Shop API, version: 2.0.0}
servers:
  - url: https://api.shop.example.com/v1
  - url: http://localhost:8080
paths:
  /orders:
    get: {operationId: listOrders, summary: List orders}
    post:
      operationId: createOrder
      security: [{oauth2: [write]}]
      requestBody:
        content:
          application/json: {schema: {type: object}}
  /orders/{id}:
    get: {operationId: getOrder, parameters: [{name: id, in: path, required: true, schema: {type: string}}]}
    delete: {operationId: deleteOrder, security: [{apiKey: []}]}
  /admin/users:
    get: {operationId: adminUsers, security: [{bearer: []}]}
components:
  securitySchemes:
    oauth2: {type: oauth2, flows: {clientCredentials: {tokenUrl: https://auth/token, scopes: {write: w}}}}
    apiKey: {type: apiKey, in: header, name: X-Key}
    bearer: {type: http, scheme: bearer}
"""

_SWAGGER2 = """
swagger: "2.0"
info: {title: Legacy, version: "1"}
host: api.legacy.example.com
basePath: /v2
schemes: [https]
paths:
  /ping: {get: {operationId: ping}}
securityDefinitions:
  key: {type: apiKey, name: api_key, in: header}
"""


@pytest.mark.parametrize("text,fn", [(_OPENAPI_RICH, "rich.yaml"), (_SWAGGER2, "swagger.yaml")])
def test_openapi_variants(text: str, fn: str) -> None:
    r = import_openapi_text(text, filename=fn)
    assert r.document.components
    assert isinstance(r.inferences, list)


def test_openapi_from_json_text() -> None:
    spec = json.dumps(
        {
            "openapi": "3.0.0",
            "info": {"title": "J", "version": "1"},
            "servers": [{"url": "https://j.example.com"}],
            "paths": {"/x": {"get": {"operationId": "x"}}},
        }
    )
    r = import_openapi_text(spec, filename="j.json")
    assert r.document is not None


def test_openapi_invalid_raises() -> None:
    # The input is neither YAML nor JSON, so it must fail while parsing — not later, with
    # some AttributeError from code that assumed a mapping came back.
    with pytest.raises(ValueError, match="interpretar como YAML/JSON"):
        import_openapi_text("this: is: not: openapi: :::", filename="bad.yaml")


# --- Kubernetes variety ---

_K8S_RICH = """
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata: {name: web, annotations: {nginx.ingress.kubernetes.io/ssl-redirect: "true"}}
spec:
  tls: [{hosts: [shop.example.com], secretName: tls-secret}]
  rules:
  - host: shop.example.com
    http: {paths: [{path: /, pathType: Prefix, backend: {service: {name: web, port: {number: 80}}}}]}
---
apiVersion: v1
kind: Service
metadata: {name: web}
spec: {type: LoadBalancer, selector: {app: web}, ports: [{port: 443, targetPort: 8443}]}
---
apiVersion: apps/v1
kind: Deployment
metadata: {name: web}
spec:
  replicas: 3
  selector: {matchLabels: {app: web}}
  template:
    metadata: {labels: {app: web}}
    spec:
      containers:
      - name: web
        image: shop/web:2.1.0
        ports: [{containerPort: 8443}]
        env: [{name: DB_URL, valueFrom: {secretKeyRef: {name: db, key: url}}}]
        securityContext: {runAsNonRoot: true, readOnlyRootFilesystem: true}
---
apiVersion: v1
kind: Secret
metadata: {name: db}
type: Opaque
data: {url: dXJs}
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: deny-all}
spec: {podSelector: {}, policyTypes: [Ingress]}
"""


def test_k8s_rich_multikind() -> None:
    r = import_kubernetes_text(_K8S_RICH, filename="stack.yaml")
    assert r.document.components
    assert r.document.data_flows is not None


def test_k8s_empty_doc() -> None:
    r = import_kubernetes_text("apiVersion: v1\nkind: ConfigMap\nmetadata: {name: c}\n", filename="cm.yaml")
    assert r.document is not None


# --- Terraform variety ---

_TF_RICH = """
provider "aws" { region = "us-east-1" }
resource "aws_s3_bucket" "data" { bucket = "data" }
resource "aws_s3_bucket_public_access_block" "data" {
  bucket = aws_s3_bucket.data.id
  block_public_acls = false
}
resource "aws_db_instance" "db" { engine = "mysql"; publicly_accessible = true }
resource "aws_security_group" "open" {
  ingress { from_port = 0; to_port = 65535; cidr_blocks = ["0.0.0.0/0"] }
}
resource "aws_iam_role" "r" { name = "r" }
resource "aws_lambda_function" "fn" { function_name = "fn"; runtime = "python3.11" }
resource "aws_instance" "vm" { ami = "ami-123"; instance_type = "t3.micro" }
"""


def test_terraform_rich() -> None:
    r = import_terraform_text(_TF_RICH, filename="main.tf")
    assert r.document.components
    assert any(i.source == "terraform" for i in r.inferences) or r.inferences == []


def test_terraform_empty() -> None:
    r = import_terraform_text("# no resources\n", filename="empty.tf")
    assert r.document is not None


# --- repo scan variety ---


def test_repo_scan_node_signals(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "svc", "dependencies": {"express": "^4", "multer": "^1"}}), encoding="utf-8"
    )
    (tmp_path / "app.js").write_text(
        "const express=require('express');const multer=require('multer');\n"
        "const app=express();const upload=multer();\n"
        "app.use(require('express-session')({secret:'x'}));\n"
        "app.get('/u',(q,s)=>s.json([]));\n"
        "app.post('/up',upload.single('f'),(q,s)=>{fetch('http://x');eval(q.body.c);});\n"
        "require('child_process').exec('ls');\n",
        encoding="utf-8",
    )
    payload = scan_node_express_repo(tmp_path)
    assert isinstance(payload, dict)


def test_repo_scan_empty_dir(tmp_path: Path) -> None:
    payload = scan_node_express_repo(tmp_path)
    assert isinstance(payload, dict)


def test_repo_scan_node_all_signals(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps({"name": "svc", "dependencies": {"express": "^4", "multer": "^1", "passport": "^0"}}),
        encoding="utf-8",
    )
    (tmp_path / "server.js").write_text(
        "const express=require('express');const multer=require('multer');\n"
        "const session=require('express-session');const passport=require('passport');\n"
        "const cp=require('child_process');const axios=require('axios');\n"
        "const app=express();const router=express.Router();\n"
        "app.use(session({secret:'s'}));app.use(passport.initialize());\n"
        "app.use('/api', router);\n"
        "router.get('/admin/users',(q,s)=>s.json([]));\n"
        "router.get('/debug',(q,s)=>s.send('d'));\n"
        "app.post('/upload', multer().single('f'), (q,s)=>{ axios('http://x'); eval(q.body.c); });\n"
        "cp.exec('ls');\n"
        "function isAuthenticated(){return true;}\n",
        encoding="utf-8",
    )
    payload = scan_node_express_repo(tmp_path)
    assert isinstance(payload, dict)


def test_repo_scan_python_signals_repo(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        "from fastapi import FastAPI, UploadFile, Depends\n"
        "import httpx, uvicorn\n"
        "app = FastAPI()\n"
        "def get_user(token: str = Depends(lambda: None)): return token\n"
        "@app.post('/admin/upload')\n"
        "async def up(file: UploadFile, user=Depends(get_user)):\n"
        "    httpx.get('http://x'); return {}\n"
        "@app.get('/debug')\n"
        "def dbg(): return {}\n",
        encoding="utf-8",
    )
    (tmp_path / "flask_app.py").write_text(
        "from flask import Flask, Blueprint\napp = Flask(__name__)\n@app.route('/x')\ndef x(): return 'x'\n",
        encoding="utf-8",
    )
    payload = scan_node_express_repo(tmp_path)
    assert isinstance(payload, dict)


# --- Helm ---

_HELM_RICH = """
apiVersion: v2
name: shop
description: Shop release
image:
  repository: shop/web
  tag: "2.1.0"
ingress:
  enabled: true
  hosts: [{host: shop.example.com}]
  tls: [{secretName: shop-tls}]
resources:
  limits: {cpu: "1", memory: 512Mi}
env:
  - name: OPENAI_API_KEY
    value: "sk-xxx"
  - name: VECTOR_DB_URL
    value: "http://qdrant:6333"
autoscaling:
  enabled: true
serviceAccount:
  create: true
"""


def test_helm_rich_values() -> None:
    r = import_helm_text(_HELM_RICH, filename="values.yaml")
    assert r.document.components
    assert isinstance(r.inferences, list)


def test_terraform_path_file_and_dir(tmp_path: Path) -> None:
    f = tmp_path / "main.tf"
    f.write_text(_TF_KINDS, encoding="utf-8")
    assert import_terraform_path(f).document is not None
    d = tmp_path / "infra"
    d.mkdir()
    (d / "a.tf").write_text('resource "aws_s3_bucket" "b" { bucket = "x" }\n', encoding="utf-8")
    (d / "b.tf").write_text('resource "aws_lb" "l" {}\n', encoding="utf-8")
    assert import_terraform_path(d).document is not None


def test_helm_path_file_and_dir(tmp_path: Path) -> None:
    f = tmp_path / "values.yaml"
    f.write_text(_HELM_RICH, encoding="utf-8")
    assert import_helm_path(f).document is not None
    d = tmp_path / "chart"
    d.mkdir()
    (d / "Chart.yaml").write_text("apiVersion: v2\nname: c\n", encoding="utf-8")
    (d / "values.yaml").write_text(_HELM_RICH, encoding="utf-8")
    assert import_helm_path(d).document is not None


def test_helm_empty_yields_minimal_draft() -> None:
    r = import_helm_text("# empty\n", filename="chart.yaml")
    assert r.document is not None
    assert r.unknowns  # "sem sinais parseáveis" path


def test_k8s_ingress_only() -> None:
    text = (
        "apiVersion: networking.k8s.io/v1\nkind: Ingress\n"
        "metadata: {name: only}\nspec: {rules: [{host: a.example.com}]}\n"
    )
    r = import_kubernetes_text(text, filename="ing.yaml")
    assert r.document is not None


_TF_KINDS = """
resource "aws_dynamodb_table" "t" { name = "t" }
resource "aws_sqs_queue" "q" {}
resource "aws_sns_topic" "n" {}
resource "aws_lb" "alb" {}
resource "aws_api_gateway_rest_api" "gw" {}
resource "google_storage_bucket" "g" {}
resource "azurerm_sql_database" "d" {}
resource "aws_ecs_service" "svc" {}
resource "aws_instance" "vm" {}
resource "kubernetes_deployment" "k" {}
resource "helm_release" "h" {}
resource "random_id" "r" {}
"""


def test_terraform_all_resource_kinds() -> None:
    r = import_terraform_text(_TF_KINDS, filename="kinds.tf")
    assert r.document.components
    kinds = {c.kind.value for c in r.document.components}
    # datastore (dynamodb/storage/sql), queue (sqs/sns), gateway (lb/gateway), process (ecs/instance)
    assert {"datastore", "queue", "gateway", "process"} & kinds


def test_terraform_empty_whitespace() -> None:
    r = import_terraform_text("   \n  \n", filename="blank.tf")
    assert any("vazio" in u.lower() for u in r.unknowns)


def test_terraform_public_gateway_wide_net() -> None:
    # Load balancer (GATEWAY) with a 0.0.0.0/0 rule -> public gateway + external flow.
    tf = (
        'resource "aws_lb" "alb" {\n'
        '  ingress { cidr_blocks = ["0.0.0.0/0"] }\n'
        "}\n"
        'resource "helm_release" "h" { name = "x" }\n'
    )
    r = import_terraform_text(tf, filename="lb.tf")
    assert r.document.data_flows  # external -> gateway flow created
    assert any("0.0.0.0/0" in i.message or "exposi" in i.message.lower() for i in r.inferences)


def test_terraform_iam_and_lambda_only() -> None:
    text = 'resource "aws_iam_policy" "p" { policy = "{}" }\nresource "aws_lambda_function" "f" { runtime = "nodejs20.x" }\n'
    r = import_terraform_text(text, filename="iam.tf")
    assert r.document is not None


def test_openapi_no_servers_no_security() -> None:
    text = "openapi: 3.0.0\ninfo: {title: Bare, version: '1'}\npaths: {/p: {get: {operationId: p}}}\n"
    r = import_openapi_text(text, filename="bare.yaml")
    assert r.document is not None


# --- K8s Ingress→Service flow branches (modern + legacy + missing) ---

_K8S_INGRESS_FLOWS = """
apiVersion: v1
kind: Service
metadata: {name: web}
spec: {selector: {app: web}, ports: [{port: 80}]}
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata: {name: ing}
spec:
  rules:
  - host: a.example.com
    http:
      paths:
      - {path: /, pathType: Prefix, backend: {service: {name: web, port: {number: 80}}}}
      - {path: /legacy, backend: {serviceName: legacy-svc, servicePort: 8080}}
      - {path: /missing, backend: {service: {name: ghost, port: {number: 9}}}}
  - http:
      paths:
      - {path: /nohost, backend: {service: {name: web}}}
"""


def test_k8s_ingress_service_flows_modern_legacy_missing() -> None:
    # Multi-rule Ingress (modern backend.service, legacy serviceName, missing service, no host).
    r = import_kubernetes_text(_K8S_INGRESS_FLOWS, filename="ingress-flows.yaml")
    assert r.document is not None
    assert r.document.components
    # Ingress references a service that does not exist in the manifest set -> recorded as unknown.
    assert any("ghost" in u for u in r.unknowns)


def test_k8s_crd_only_inference() -> None:
    text = (
        "apiVersion: apiextensions.k8s.io/v1\nkind: CustomResourceDefinition\n"
        "metadata: {name: widgets.example.com}\nspec: {group: example.com}\n"
    )
    r = import_kubernetes_text(text, filename="crd.yaml")
    assert r.document is not None


def test_k8s_helm_chart_content_note() -> None:
    text = "# Chart.yaml\napiVersion: v2\nname: x\n"
    r = import_kubernetes_text(text, filename="mixed.yaml")
    assert any("Helm" in u for u in r.unknowns)


def test_k8s_path_directory_and_empty(tmp_path: Path) -> None:
    d = tmp_path / "manifests"
    d.mkdir()
    (d / "svc.yaml").write_text(
        "apiVersion: v1\nkind: Service\nmetadata: {name: s}\nspec: {ports: [{port: 80}]}\n", encoding="utf-8"
    )
    r = import_kubernetes_path(d)
    assert r.document is not None
    empty = tmp_path / "empty"
    empty.mkdir()
    r2 = import_kubernetes_path(empty)
    assert any("Directório sem" in u for u in r2.unknowns)
