"""Smoke suite objetiva para release candidate."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from otm_cli.cli import app
from otm_core_schema import Metadata, load_document_from_yaml_path
from typer.testing import CliRunner

from otm_api.main import app as api_app

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(api_app)


def test_smoke_cli_basic_flow(runner: CliRunner) -> None:
    assert runner.invoke(app, ["validate", str(_MINIMAL)]).exit_code == 0
    assert runner.invoke(app, ["analyze", str(_MINIMAL), "--methodology", "stride"]).exit_code == 0
    assert runner.invoke(app, ["export", str(_MINIMAL), "--format", "md"]).exit_code == 0


def test_smoke_api_basic_flow(client: TestClient) -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_dump(mode="json", by_alias=True)
    assert client.get("/health").status_code == 200
    assert client.post("/v1/models/validate", json={"document": doc}).status_code == 200
    assert client.post("/v1/models/analyze", json={"document": doc}).status_code == 200
    assert client.post(
        "/v1/exports",
        json={"document": doc, "formats": ["analysis_markdown"]},
    ).status_code == 200


@pytest.mark.parametrize(
    "methodology,title_keyword",
    [
        ("stride", "API"),
        ("linddun", "LGPD"),
        ("pasta", "risk-centric"),
        ("plot4ai", "LLM"),
    ],
)
def test_smoke_methodology_analysis(
    client: TestClient, methodology: str, title_keyword: str
) -> None:
    base = load_document_from_yaml_path(_MINIMAL)
    doc = base.model_copy(update={"metadata": Metadata(title=f"Sistema {title_keyword}")})
    r = client.post(
        "/v1/models/analyze",
        json={
            "document": doc.model_dump(mode="json", by_alias=True),
            "methodology": methodology,
        },
    )
    assert r.status_code == 200
    out = r.json()
    assert out["methodology"] == methodology
    assert "summary" in out
