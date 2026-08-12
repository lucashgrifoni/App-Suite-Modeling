"""
Regressão: um `pack_id` desconhecido é sempre 404 `PACK_NOT_FOUND`, em todas as rotas.

`PACK_NOT_FOUND`/404 é um código estável documentado (docs/features/API.md). Qualquer
rota que consiga correr o motor tem de mapear o `FileNotFoundError` do loader para esse
404 — caso contrário o erro de cliente sai como 500 `INTERNAL_ERROR`, sem código e sem
a lista de packs válidos.
"""

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


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _doc() -> dict[str, Any]:
    return load_document_from_yaml_path(_MINIMAL).model_dump(mode="json", by_alias=True)


def _payload_for(path: str, pack_id: str) -> dict[str, Any]:
    d = _doc()
    if "compare" in path:
        return {"baseline": d, "revised": d, "run_analysis": True, "pack_id": pack_id}
    if "exports" in path:
        # `analysis_json` obriga a correr o motor; `document_json` (default) não o faria.
        return {"document": d, "formats": ["analysis_json"], "pack_id": pack_id}
    if "premium" in path or "remediation" in path:
        return {"document": d, "run_analysis": True, "pack_id": pack_id}
    return {"document": d, "pack_id": pack_id}


_ENGINE_ROUTES = [
    "/v1/models/analyze",
    "/v1/exports",
    "/v1/models/compare",
    "/v1/reports/premium",
    "/v1/remediation/backlog",
    "/v1/remediation/backlog?format=markdown",
]


@pytest.mark.parametrize("path", _ENGINE_ROUTES)
def test_unknown_pack_id_is_404_pack_not_found(client: TestClient, path: str) -> None:
    r = client.post(path, json=_payload_for(path, "nope"))
    assert r.status_code == 404, f"{path} -> {r.status_code} {r.text[:200]}"
    detail = r.json()["detail"]
    assert detail["code"] == "PACK_NOT_FOUND"
    # A mensagem tem de nomear os packs válidos — é o que a torna acionável.
    assert "saas" in detail["message"]


@pytest.mark.parametrize("path", _ENGINE_ROUTES)
def test_blank_pack_id_is_rejected_like_any_other_unknown_pack(client: TestClient, path: str) -> None:
    """`pack_id: ""` era aceite em silêncio (200 sem pack), enquanto `" "` dava 404."""
    r = client.post(path, json=_payload_for(path, ""))
    assert r.status_code == 404, f"{path} -> {r.status_code} {r.text[:200]}"
    assert r.json()["detail"]["code"] == "PACK_NOT_FOUND"


@pytest.mark.parametrize("path", _ENGINE_ROUTES)
def test_whitespace_pack_id_stays_404(client: TestClient, path: str) -> None:
    r = client.post(path, json=_payload_for(path, " "))
    assert r.status_code == 404, f"{path} -> {r.status_code} {r.text[:200]}"


def test_omitted_pack_id_still_runs_without_a_pack(client: TestClient) -> None:
    """Controlo: ausência de `pack_id` (ou `null`) continua a ser 'sem pack', não erro."""
    d = _doc()
    assert client.post("/v1/models/analyze", json={"document": d}).status_code == 200
    assert client.post("/v1/models/analyze", json={"document": d, "pack_id": None}).status_code == 200
