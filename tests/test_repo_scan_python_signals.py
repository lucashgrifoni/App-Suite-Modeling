"""Sinais adicionais do varrimento Python (rotas, upload, HTTP externo, auth)."""

from __future__ import annotations

from pathlib import Path

from otm_artifact_import import scan_node_express_repo


def test_scan_python_routes_upload_and_external_http(tmp_path: Path) -> None:
    (tmp_path / "api.py").write_text(
        '''
from fastapi import FastAPI, UploadFile, Depends
import httpx

app = FastAPI()

@app.post("/items")
async def create(file: UploadFile):
    r = httpx.get("https://example.com")
    return {"ok": True}

@app.get("/admin/stats")
def admin():
    return {}
''',
        encoding="utf-8",
    )
    out = scan_node_express_repo(tmp_path)
    kinds = {x["kind"] for x in out["inferences"]}
    assert "python_route" in kinds
    assert "python_upload" in kinds
    assert "python_external_http" in kinds
    assert "admin_route" in kinds
    hints = out.get("modeling_hints") or []
    bases = {h.get("basis") for h in hints}
    assert "repo_inference:python_upload" in bases
    assert "repo_inference:python_external_http" in bases
