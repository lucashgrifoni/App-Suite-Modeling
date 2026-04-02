"""Varredura pragmática Node/Express."""

from __future__ import annotations

from pathlib import Path

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
    kinds = {x["kind"] for x in out["inferences"]}
    assert "route" in kinds
    assert "upload" in kinds or "session" in kinds or "fetch" in kinds
