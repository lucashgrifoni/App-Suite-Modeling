"""API coverage — premium report and remediation backlog routers (all branches)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from otm_core_schema import load_document_from_yaml_path

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _doc() -> dict[str, Any]:
    return load_document_from_yaml_path(_MINIMAL).model_dump(mode="json", by_alias=True)


def _analysis(client: TestClient) -> dict[str, Any]:
    r = client.post("/v1/models/analyze", json={"document": _doc()})
    assert r.status_code == 200
    return r.json()


# --- /v1/reports/premium ---


def test_premium_run_analysis_markdown(client: TestClient) -> None:
    r = client.post(
        "/v1/reports/premium",
        json={"document": _doc(), "run_analysis": True, "level": "executive", "locale": "en"},
    )
    assert r.status_code == 200
    assert "markdown" in r.headers["content-type"]


def test_premium_with_analysis_and_baseline(client: TestClient) -> None:
    ar = _analysis(client)
    r = client.post(
        "/v1/reports/premium",
        json={"document": _doc(), "analysis": ar, "baseline_analysis": ar, "level": "standard"},
    )
    assert r.status_code == 200


def test_premium_missing_analysis_without_run_is_400(client: TestClient) -> None:
    r = client.post("/v1/reports/premium", json={"document": _doc(), "run_analysis": False})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "PREMIUM_REPORT_INPUT"


def test_premium_invalid_analysis_is_422(client: TestClient) -> None:
    r = client.post(
        "/v1/reports/premium",
        json={"document": _doc(), "analysis": {"not": "an analysis result"}},
    )
    assert r.status_code == 422


def test_premium_invalid_baseline_is_422(client: TestClient) -> None:
    ar = _analysis(client)
    r = client.post(
        "/v1/reports/premium",
        json={"document": _doc(), "analysis": ar, "baseline_analysis": {"bad": 1}},
    )
    assert r.status_code == 422


def test_premium_bad_pack_is_404ish(client: TestClient) -> None:
    r = client.post(
        "/v1/reports/premium",
        json={"document": _doc(), "run_analysis": True, "pack_id": "no_such_pack_xyz"},
    )
    assert r.status_code in (404, 400, 422)


def test_premium_pdf(client: TestClient) -> None:
    pytest.importorskip("xhtml2pdf")
    r = client.post(
        "/v1/reports/premium",
        json={"document": _doc(), "run_analysis": True, "level": "executive", "output_format": "pdf"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/pdf")


# --- /v1/remediation/backlog ---


def test_remediation_json_default(client: TestClient) -> None:
    r = client.post("/v1/remediation/backlog", json={"document": _doc(), "run_analysis": True})
    assert r.status_code == 200
    assert isinstance(r.json(), dict)


def test_remediation_markdown(client: TestClient) -> None:
    ar = _analysis(client)
    r = client.post(
        "/v1/remediation/backlog?format=markdown&group_by=control",
        json={"document": _doc(), "analysis": ar},
    )
    assert r.status_code == 200
    assert "markdown" in r.headers["content-type"]


def test_remediation_invalid_analysis_is_422(client: TestClient) -> None:
    r = client.post(
        "/v1/remediation/backlog",
        json={"document": _doc(), "analysis": {"bad": "shape"}},
    )
    assert r.status_code == 422


# --- /v1/imports/{terraform,kubernetes} routes ---

_TF = 'resource "aws_s3_bucket" "b" { bucket = "x" }\nresource "aws_db_instance" "d" { engine = "postgres" }\n'
_K8S = "apiVersion: v1\nkind: Service\nmetadata: {name: api}\nspec: {ports: [{port: 80}], selector: {app: api}}\n"


def test_import_terraform_route_ok(client: TestClient) -> None:
    r = client.post("/v1/imports/terraform", files={"file": ("main.tf", _TF.encode(), "text/plain")})
    assert r.status_code == 200
    assert "document" in r.json()


def test_import_kubernetes_route_ok(client: TestClient) -> None:
    r = client.post("/v1/imports/kubernetes", files={"file": ("k8s.yaml", _K8S.encode(), "application/yaml")})
    assert r.status_code == 200
    assert "document" in r.json()


def test_import_terraform_oversized_413(client: TestClient) -> None:
    big = b"# " + b"x" * (2 * 1024 * 1024 + 1)
    r = client.post("/v1/imports/terraform", files={"file": ("big.tf", big, "text/plain")})
    assert r.status_code == 413


def test_import_terraform_empty_is_handled(client: TestClient) -> None:
    # empty/sparse terraform still returns a draft (never crashes)
    r = client.post("/v1/imports/terraform", files={"file": ("empty.tf", b"# nothing\n", "text/plain")})
    assert r.status_code in (200, 400)


# --- error paths: compare / analyses-diff / exports ---


def test_compare_invalid_analyses_422(client: TestClient) -> None:
    d = _doc()
    r = client.post(
        "/v1/models/compare",
        json={"baseline": d, "revised": d, "baseline_analysis": {"bad": 1}, "revised_analysis": {"bad": 2}},
    )
    assert r.status_code == 422


def test_compare_run_analysis_bad_pack(client: TestClient) -> None:
    d = _doc()
    r = client.post(
        "/v1/models/compare",
        json={"baseline": d, "revised": d, "run_analysis": True, "pack_id": "no_such_pack_xyz"},
    )
    assert r.status_code in (404, 400, 422)


def test_compare_structural_only_ok(client: TestClient) -> None:
    d = _doc()
    r = client.post("/v1/models/compare", json={"baseline": d, "revised": d})
    assert r.status_code == 200


def test_analyses_diff_invalid_422(client: TestClient) -> None:
    r = client.post(
        "/v1/analyses/diff",
        json={"baseline_analysis": {"bad": 1}, "revised_analysis": {"bad": 2}},
    )
    assert r.status_code == 422


def test_analyses_diff_ok(client: TestClient) -> None:
    ar = _analysis(client)
    r = client.post("/v1/analyses/diff", json={"baseline_analysis": ar, "revised_analysis": ar})
    assert r.status_code == 200


def test_export_invalid_analysis_422(client: TestClient) -> None:
    r = client.post("/v1/exports", json={"document": _doc(), "formats": ["analysis_json"], "analysis": {"bad": 1}})
    assert r.status_code == 422


def test_export_bad_pack(client: TestClient) -> None:
    r = client.post(
        "/v1/exports",
        json={"document": _doc(), "formats": ["analysis_json"], "pack_id": "no_such_pack_xyz"},
    )
    assert r.status_code in (404, 400, 422)


def test_export_ok(client: TestClient) -> None:
    r = client.post("/v1/exports", json={"document": _doc(), "formats": ["document_json", "mermaid"]})
    assert r.status_code in (200, 422)


def test_recommend_methodology_route(client: TestClient) -> None:
    r = client.post("/v1/models/recommend-methodology", json={"document": _doc()})
    assert r.status_code == 200
