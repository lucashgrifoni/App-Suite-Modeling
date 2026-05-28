"""CLI coverage — `otm import` subcommands (openapi/terraform/k8s/repo).

Exercises both output modes (stdout vs file), the --explain-out / --json-out
branches, the inference summary panel, and the CliUserError path for bad inputs.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from otm_cli.cli import app
from typer.testing import CliRunner

_OPENAPI = """
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


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


# --- OpenAPI ---


def test_import_openapi_stdout(runner: CliRunner, tmp_path: Path) -> None:
    spec = tmp_path / "api.yaml"
    spec.write_text(_OPENAPI, encoding="utf-8")
    r = runner.invoke(app, ["import", "openapi", str(spec)])
    assert r.exit_code == 0
    assert "schema_version" in (r.stdout + (r.stderr or ""))


def test_import_openapi_to_file_with_explain_and_summary(runner: CliRunner, tmp_path: Path) -> None:
    spec = tmp_path / "api.yaml"
    spec.write_text(_OPENAPI, encoding="utf-8")
    out = tmp_path / "draft.otm.yaml"
    explain = tmp_path / "explain.json"
    r = runner.invoke(
        app,
        ["import", "openapi", str(spec), "-o", str(out), "--explain-out", str(explain)],
    )
    assert r.exit_code == 0
    assert out.is_file() and explain.is_file()
    payload = json.loads(explain.read_text(encoding="utf-8"))
    assert "document" in payload and "inferences" in payload


def test_import_openapi_missing_file_errors(runner: CliRunner, tmp_path: Path) -> None:
    r = runner.invoke(app, ["import", "openapi", str(tmp_path / "nope.yaml")])
    assert r.exit_code == 1


# --- Terraform ---


def test_import_terraform_stdout(runner: CliRunner, tmp_path: Path) -> None:
    tf = tmp_path / "infra.tf"
    tf.write_text(_TERRAFORM, encoding="utf-8")
    r = runner.invoke(app, ["import", "terraform", str(tf)])
    assert r.exit_code == 0
    assert "schema_version" in (r.stdout + (r.stderr or ""))


def test_import_terraform_to_file_with_explain(runner: CliRunner, tmp_path: Path) -> None:
    tf = tmp_path / "infra.tf"
    tf.write_text(_TERRAFORM, encoding="utf-8")
    out = tmp_path / "tf.otm.yaml"
    explain = tmp_path / "tf.json"
    r = runner.invoke(
        app,
        ["import", "terraform", str(tf), "-o", str(out), "--explain-out", str(explain)],
    )
    assert r.exit_code == 0
    assert out.is_file() and explain.is_file()


def test_import_terraform_missing_path_errors(runner: CliRunner, tmp_path: Path) -> None:
    r = runner.invoke(app, ["import", "terraform", str(tmp_path / "absent.tf")])
    assert r.exit_code == 1


# --- Kubernetes ---


def test_import_k8s_stdout(runner: CliRunner, tmp_path: Path) -> None:
    man = tmp_path / "k8s.yaml"
    man.write_text(_K8S, encoding="utf-8")
    r = runner.invoke(app, ["import", "k8s", str(man)])
    assert r.exit_code == 0
    assert "schema_version" in (r.stdout + (r.stderr or ""))


def test_import_k8s_to_file_with_explain(runner: CliRunner, tmp_path: Path) -> None:
    man = tmp_path / "k8s.yaml"
    man.write_text(_K8S, encoding="utf-8")
    out = tmp_path / "k8s.otm.yaml"
    explain = tmp_path / "k8s.json"
    r = runner.invoke(
        app,
        ["import", "k8s", str(man), "-o", str(out), "--explain-out", str(explain)],
    )
    assert r.exit_code == 0
    assert out.is_file() and explain.is_file()


def test_import_k8s_missing_path_errors(runner: CliRunner, tmp_path: Path) -> None:
    r = runner.invoke(app, ["import", "k8s", str(tmp_path / "absent.yaml")])
    assert r.exit_code == 1


# --- repo scan ---


def _make_node_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "package.json").write_text(json.dumps({"name": "svc", "dependencies": {"express": "^4"}}), encoding="utf-8")
    (root / "server.js").write_text(
        "const express = require('express');\n"
        "const app = express();\n"
        "app.get('/users', (req, res) => res.json([]));\n"
        "app.post('/upload', (req, res) => { eval(req.body.x); });\n",
        encoding="utf-8",
    )


def test_import_repo_panel(runner: CliRunner, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _make_node_repo(repo)
    r = runner.invoke(app, ["import", "repo", str(repo)])
    assert r.exit_code == 0
    assert "repo-scan" in (r.stdout + (r.stderr or ""))


def test_import_repo_json_out(runner: CliRunner, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _make_node_repo(repo)
    out = tmp_path / "scan.json"
    r = runner.invoke(app, ["import", "repo", str(repo), "--json-out", str(out)])
    assert r.exit_code == 0
    assert out.is_file()
    json.loads(out.read_text(encoding="utf-8"))


def test_import_repo_not_a_dir_errors(runner: CliRunner, tmp_path: Path) -> None:
    f = tmp_path / "afile.txt"
    f.write_text("x", encoding="utf-8")
    r = runner.invoke(app, ["import", "repo", str(f)])
    assert r.exit_code == 1
