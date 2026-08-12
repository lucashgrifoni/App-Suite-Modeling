"""Security regression — pack/template id path traversal + domain-422 input disclosure.

Reproduces and locks the fix for the confirmed unauthenticated arbitrary-`.yaml`
file read via `pack_id`: a traversal/absolute id pointed `load_pack` at a file
outside `data/packs/` and the domain 422 echoed its full parsed contents.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient
from otm_api.main import app
from otm_api.routers._errors import _pydantic_error_items
from otm_industry_packs.loader import (
    list_pack_ids,
    list_template_ids,
    load_pack,
    load_template_info,
    load_template_yaml,
)
from pydantic import BaseModel, ValidationError

_TRAVERSAL_IDS = [
    "../../../../etc/passwd",
    "../" * 8 + "etc/hosts",
    "/etc/hosts",
    "packs/../../secret",
    "..\\..\\..\\windows\\win.ini",
]


def test_load_pack_rejects_traversal_and_absolute_paths(tmp_path: Path) -> None:
    sentinel = tmp_path / "evil.yaml"
    sentinel.write_text("leaked: 1\n", encoding="utf-8")
    candidates = [*_TRAVERSAL_IDS, str(sentinel)[:-5], str(sentinel).replace("\\", "/")[:-5], "nonexistent-pack"]
    for bad in candidates:
        with pytest.raises(FileNotFoundError):
            load_pack(bad)


def test_load_template_rejects_traversal() -> None:
    for bad in _TRAVERSAL_IDS:
        with pytest.raises(FileNotFoundError):
            load_template_yaml(bad)
        assert load_template_info(bad) is None


def test_known_catalog_ids_still_load() -> None:
    packs = list_pack_ids()
    assert packs, "embedded pack catalog should be present"
    assert load_pack(packs[0]) is not None
    templates = list_template_ids()
    assert templates, "embedded template catalog should be present"
    assert isinstance(load_template_yaml(templates[0]), str)


def test_compare_endpoint_does_not_leak_file_contents_via_pack_id(tmp_path: Path) -> None:
    secret = "DO_NOT_LEAK_SENTINEL_x9f3"
    sentinel = tmp_path / "sentinel.yaml"
    sentinel.write_text(f"leaked_marker: '{secret}'\nrows: [1, 2, 3]\n", encoding="utf-8")
    doc = yaml.safe_load(Path("examples/minimal.otm.yaml").read_text(encoding="utf-8"))
    pack_id = str(sentinel).replace("\\", "/")[:-5]  # load_pack re-appends `.yaml`

    client = TestClient(app)
    resp = client.post(
        "/v1/models/compare",
        json={"baseline": doc, "revised": doc, "run_analysis": True, "pack_id": pack_id},
    )

    assert resp.status_code == 404, resp.text
    assert secret not in resp.text


def test_domain_422_truncates_echoed_input() -> None:
    class _M(BaseModel):
        x: int

    with pytest.raises(ValidationError) as excinfo:
        _M.model_validate({"x": "Z" * 5000})
    items = _pydantic_error_items(excinfo.value)

    echoed = str(items[0].get("input", ""))
    assert "chars suppressed" in echoed
    assert len(echoed) < 5000
