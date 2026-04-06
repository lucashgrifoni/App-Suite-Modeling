"""Varredura pragmática Node/Express."""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_artifact_import import scan_node_express_repo


def test_scan_node_express_repo_finds_route_and_signals(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    (src / "app.js").write_text(
        """
const express = require('express');
const multer = require('multer');
const session = require('express-session');
const axios = require('axios');
const app = express();
app.get('/admin', (req, res) => res.send('ok'));
app.post('/upload', upload.single('x'), handler);
eval('0');
""",
        encoding="utf-8",
    )
    out = scan_node_express_repo(tmp_path)
    assert "modeling_hints" in out and isinstance(out["modeling_hints"], list)
    assert "import_signals_corpus_snippets" in out
    kinds = {x["kind"] for x in out["inferences"]}
    assert "route" in kinds
    assert "upload" in kinds or "session" in kinds or "fetch" in kinds
    routes = [x for x in out["inferences"] if x["kind"] == "route"]
    assert routes
    assert all(x.get("inference_source") in ("regex_heuristic", "combined", "ast_lite") for x in routes)
    stacks = out.get("detected_stacks") or []
    assert "javascript_family" in stacks


def test_scan_detects_python_fastapi_signals(tmp_path: Path) -> None:
    (tmp_path / "main.py").write_text(
        """
from fastapi import FastAPI
app = FastAPI()
@app.get("/health")
def health():
    return {"ok": True}
""",
        encoding="utf-8",
    )
    out = scan_node_express_repo(tmp_path)
    stacks = out.get("detected_stacks") or []
    assert "python_family" in stacks
    assert any(x.get("stack_hint") == "python_fastapi" for x in out["inferences"])


def test_scan_node_express_ast_only_route_when_esprima_enabled(tmp_path, monkeypatch):
    pytest.importorskip("esprima")
    monkeypatch.setenv("OTM_REPO_ESPRIMA", "1")
    src = tmp_path / "routes.js"
    src.write_text(
        """
const express = require('express');
const r = express.Router();
r.get('/only-via-ast', (req, res) => res.send('x'));
module.exports = r;
""",
        encoding="utf-8",
    )
    out = scan_node_express_repo(tmp_path)
    ast_routes = [x for x in out["inferences"] if x.get("inference_source") == "ast_lite"]
    assert any("only-via-ast" in (x.get("evidence") or "") for x in ast_routes)
