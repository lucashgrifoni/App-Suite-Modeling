"""Regression — `otm import repo --draft-out` emits a valid chainable draft.

Locks down D3 from the v7.5.0 extreme-end-user validation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from otm_cli.application.import_service import (
    _short_file_id,
    _slug,
    scan_payload_to_draft_yaml,
)
from otm_cli.cli import app
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _sample_payload() -> dict:
    return {
        "root": "C:/tmp/example-service",
        "files_scanned": 4,
        "inferences": [
            {
                "kind": "route",
                "message": "Rota HTTP encontrada em `src\\routes\\admin.js`",
                "evidence": "/admin/users",
                "confidence": "medium",
                "inference_source": "regex_heuristic",
            },
            {
                "kind": "admin_route",
                "message": "Possível rota ou prefixo `/admin` em `src\\routes\\admin.js`",
                "evidence": "/admin",
                "confidence": "medium",
                "inference_source": "regex_heuristic",
            },
            {
                "kind": "session",
                "message": "Sessão/cookies prováveis em `src\\app.js`",
                "evidence": "express-session",
                "confidence": "medium",
                "inference_source": "regex_heuristic",
            },
            {
                "kind": "route",
                "message": "Rota HTTP encontrada em `src\\routes\\public.js`",
                "evidence": "/api/v1/products",
                "confidence": "medium",
                "inference_source": "regex_heuristic",
            },
        ],
    }


def test_slug_is_safe_for_ids() -> None:
    assert _slug("Hello World!") == "hello_world"
    assert _slug("/api/v1/payments") == "api_v1_payments"
    assert _slug("") == "x"


def test_short_file_id_uses_file_stem() -> None:
    assert _short_file_id("src/routes/admin.js") == "admin"
    assert _short_file_id("src\\routes\\admin.js") == "admin"


def test_scan_payload_to_draft_yaml_emits_valid_yaml() -> None:
    text = scan_payload_to_draft_yaml(_sample_payload())
    assert text.startswith("# Gerado por: otm import repo --draft-out")
    parsed = yaml.safe_load(text)
    assert parsed["model"]["schema_version"] == "1.1.0"
    assert any(c["id"] == "ext_user" for c in parsed["components"])
    assert any(c["id"].startswith("svc_") for c in parsed["components"])
    assert any(f["from_component"] == "ext_user" for f in parsed["data_flows"])
    # Session inference must surface a session asset.
    assert any(a["asset_kind"] == "session" for a in parsed["assets"])
    # Admin routes flagged in summary so a human notices.
    assert "/admin" in parsed["metadata"]["summary"]


def test_scan_payload_to_draft_yaml_handles_no_inferences() -> None:
    text = scan_payload_to_draft_yaml({"root": "/x", "inferences": []})
    parsed = yaml.safe_load(text)
    assert parsed["components"] == [{"id": "ext_user", "name": "Cliente externo", "kind": "external_entity"}]
    assert parsed["data_flows"] == []
    assert "Nenhuma rota detectada" in parsed["metadata"]["summary"]


def test_cli_import_repo_draft_chains_into_validate(runner: CliRunner, tmp_path: Path) -> None:
    # Minimal Node-shaped repo with one express route.
    repo = tmp_path / "svc"
    routes = repo / "src" / "routes"
    routes.mkdir(parents=True)
    (routes / "ping.js").write_text(
        "import express from 'express';\n"
        "const router = express.Router();\n"
        "router.get('/ping', (req, res) => res.json({ok:true}));\n"
        "export default router;\n",
        encoding="utf-8",
    )
    (repo / "package.json").write_text('{"name":"svc"}', encoding="utf-8")

    draft = tmp_path / "draft.otm.yaml"
    r1 = runner.invoke(app, ["import", "repo", str(repo), "--draft-out", str(draft)])
    assert r1.exit_code == 0, r1.stdout
    assert draft.exists()

    r2 = runner.invoke(app, ["validate", str(draft)])
    assert r2.exit_code == 0, r2.stdout
