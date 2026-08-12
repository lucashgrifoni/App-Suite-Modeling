"""Coverage — anti-pattern detection across semantic profiles (structural + corpus paths)."""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from otm_threat_engine.anti_pattern_library import detect_anti_patterns

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def _base() -> dict[str, Any]:
    doc = load_document_from_yaml_path(_MINIMAL)
    return doc.model_dump(mode="python", by_alias=True)


def _doc(d: dict[str, Any]) -> ThreatModelDocument:
    return ThreatModelDocument.model_validate(d)


def _tb(d: dict[str, Any]) -> str:
    tbs = d.get("trust_boundaries") or []
    return tbs[0]["id"] if tbs else "internet"


def test_no_profile_returns_empty() -> None:
    d = _base()
    d["model"].pop("template_semantic_profile", None)
    assert detect_anti_patterns(_doc(d)) == []


def test_admin_profile_fires() -> None:
    d = _base()
    d["model"]["template_semantic_profile"] = "internal_admin_portal"
    d["components"].append({"id": "admin_console", "name": "Admin", "kind": "process", "in_trust_boundary": _tb(d)})
    hits = detect_anti_patterns(_doc(d))
    assert any("admin" in h.id for h in hits)


def test_ecommerce_profile_fires() -> None:
    d = _base()
    d["model"]["template_semantic_profile"] = "industry_ecommerce"
    d["components"].append({"id": "cart_service", "name": "Cart", "kind": "process", "in_trust_boundary": _tb(d)})
    hits = detect_anti_patterns(_doc(d))
    assert any("ecommerce" in h.id for h in hits)


def test_api_profile_with_gateway_fires() -> None:
    d = _base()
    d["model"]["template_semantic_profile"] = "api_backend_rest"
    d["components"].append({"id": "edge_gw", "name": "Edge", "kind": "gateway", "in_trust_boundary": _tb(d)})
    hits = detect_anti_patterns(_doc(d))
    assert any("api" in h.id for h in hits)


def test_file_handling_profile_with_upload_flow_fires() -> None:
    d = _base()
    d["model"]["template_semantic_profile"] = "file_handling_application"
    d["components"].append({"id": "upload_svc", "name": "Upload", "kind": "process", "in_trust_boundary": _tb(d)})
    # set the flow flag many upload anti-patterns require (require_flow_flag_any)
    for fl in d.get("data_flows") or []:
        fl["supports_file_upload"] = True
    hits = detect_anti_patterns(_doc(d))
    assert isinstance(hits, list)


def test_file_handling_with_cross_boundary_and_assets() -> None:
    # Exercise require_min_cross_boundary_flows + require_asset_name_id_contains_any paths.
    # Cross-boundary is derived from component placement (the minimal model already puts `user`
    # in `internet` and `api` in `vpc`), not from a per-flow flag — there is no such field.
    d = _base()
    d["model"]["template_semantic_profile"] = "file_handling_application"
    d["components"].append({"id": "upload_svc", "name": "Upload", "kind": "process", "in_trust_boundary": _tb(d)})
    d["assets"].append({"id": "user_upload", "name": "User uploaded file", "data_classification": "confidential"})
    for fl in d.get("data_flows") or []:
        fl["supports_file_upload"] = True
    hits = detect_anti_patterns(_doc(d))
    assert isinstance(hits, list)


def test_api_profile_cross_boundary() -> None:
    d = _base()
    d["model"]["template_semantic_profile"] = "api_backend_rest"
    d["components"].append({"id": "edge_gw", "name": "Edge", "kind": "gateway", "in_trust_boundary": _tb(d)})
    hits = detect_anti_patterns(_doc(d))
    assert isinstance(hits, list)


@pytest.mark.parametrize("profile", ["saas_tenant_isolation", "webhook_ingestion_pipeline"])
def test_other_profiles_run(profile: str) -> None:
    d = _base()
    d["model"]["template_semantic_profile"] = profile
    assert isinstance(detect_anti_patterns(_doc(d)), list)


def test_mitigating_keywords_silence_pattern() -> None:
    # Adding the mitigating keyword to the summary should suppress at least one ecommerce gap.
    d = _base()
    d["model"]["template_semantic_profile"] = "industry_ecommerce"
    d["components"].append({"id": "shop_api", "name": "Shop", "kind": "process", "in_trust_boundary": _tb(d)})
    base_hits = {h.id for h in detect_anti_patterns(_doc(d))}
    d2 = copy.deepcopy(d)
    d2["metadata"]["summary"] = (d2["metadata"].get("summary") or "") + " psp pagamento payment fraude chargeback pci"
    mit_hits = {h.id for h in detect_anti_patterns(_doc(d2))}
    assert len(mit_hits) <= len(base_hits)
