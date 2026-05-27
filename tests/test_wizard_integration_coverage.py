"""Coverage — wizard context boosts/traces through a real analyze run, per semantic profile."""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from otm_threat_engine import analyze_document

_ROOT = Path(__file__).resolve().parents[1]

# profile -> (model file, tags mixing yes/no to exercise risk-signal + mitigator branches)
_CASES = {
    "industry_ecommerce": (
        "examples/test-apps/ecommerce-subscription.otm.yaml",
        [
            "wz:industry_ecommerce:checkout=yes",
            "wz:industry_ecommerce:psp_boundary=no",
            "wz:industry_ecommerce:sensitive_data=no",
        ],
    ),
    "api_backend_rest": (
        "examples/saas-ordering-v1.otm.yaml",
        [
            "wz:api_backend_rest:auth=no",
            "wz:api_backend_rest:rate_limit=no",
            "wz:api_backend_rest:edge_controls=yes",
        ],
    ),
    "internal_admin_portal": (
        "examples/test-apps/health-clinic.otm.yaml",
        [
            "wz:internal_admin_portal:approval=no",
            "wz:internal_admin_portal:segregation=no",
            "wz:internal_admin_portal:jit=yes",
        ],
    ),
    "file_handling_application": (
        "examples/test-apps/finance-wallet.otm.yaml",
        [
            "wz:file_handling_application:quarantine=no",
            "wz:file_handling_application:scan=yes",
            "wz:file_handling_application:public_objects=no",
        ],
    ),
}


def _with_profile_and_tags(model: str, profile: str, tags: list[str]) -> ThreatModelDocument:
    doc = load_document_from_yaml_path(_ROOT / model)
    d = doc.model_dump(mode="python", by_alias=True)
    d.setdefault("model", {})["template_semantic_profile"] = profile
    meta = d.setdefault("metadata", {})
    meta["tags"] = list(meta.get("tags") or []) + tags
    return ThreatModelDocument.model_validate(d)


@pytest.mark.parametrize("profile", list(_CASES))
def test_wizard_boosts_per_profile(profile: str) -> None:
    model, tags = _CASES[profile]
    doc = _with_profile_and_tags(model, profile, tags)
    res = analyze_document(doc)
    # signals matching the profile must produce wizard context output (notes and/or trace)
    assert res.wizard_signal_trace is not None
    assert isinstance(res.wizard_context_notes, list)


@pytest.mark.parametrize("profile", list(_CASES))
def test_wizard_all_yes_mitigators(profile: str) -> None:
    model, _ = _CASES[profile]
    keys = {
        "industry_ecommerce": ["checkout", "psp_boundary", "sensitive_data"],
        "api_backend_rest": ["auth", "rate_limit", "edge_controls"],
        "internal_admin_portal": ["approval", "segregation", "jit"],
        "file_handling_application": ["quarantine", "scan", "public_objects"],
    }[profile]
    tags = [f"wz:{profile}:{k}=yes" for k in keys]
    doc = _with_profile_and_tags(model, profile, tags)
    res = analyze_document(doc)
    assert res.wizard_signal_trace is not None
