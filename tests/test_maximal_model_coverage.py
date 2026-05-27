"""Coverage — a maximal synthetic model exercises risk/classify/composite/anti-pattern branches.

Sets every component kind, sensitive assets, and all data-flow risk flags, then runs the engine
across methodologies plus report/backlog, hitting many otherwise-unreached engine branches.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from otm_core_schema.enums import ThreatModelMethodology
from otm_threat_engine import analyze_document, build_remediation_backlog

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def _maximal() -> ThreatModelDocument:
    d: dict[str, Any] = load_document_from_yaml_path(_MINIMAL).model_dump(mode="python", by_alias=True)
    tb = (d.get("trust_boundaries") or [{"id": "internet"}])[0]["id"]
    d["components"].extend(
        [
            {
                "id": "admin_console", "name": "Admin Console", "kind": "process",
                "in_trust_boundary": tb, "supports_admin_operations": True, "privilege_level": "admin",
            },
            {"id": "store_db", "name": "DB", "kind": "datastore", "in_trust_boundary": tb},
            {"id": "edge_gw", "name": "Gateway", "kind": "gateway", "in_trust_boundary": tb},
            {"id": "work_q", "name": "Queue", "kind": "queue", "in_trust_boundary": tb},
            {"id": "third_party", "name": "External", "kind": "external_entity", "in_trust_boundary": tb},
        ]
    )
    d.setdefault("assets", []).append(
        {
            "id": "pii_asset", "name": "Customer PII", "data_classification": "confidential",
            "business_criticality": "critical", "related_component_ids": ["store_db"],
        }
    )
    for fl in d.get("data_flows") or []:
        fl.update(
            {
                "encrypted": False, "authenticated": False, "public_exposure": True,
                "affects_privileged_state": True, "stores_sensitive_data": True,
                "supports_file_upload": True, "input_from_untrusted_source": True,
                "supports_external_fetch": True,
            }
        )
    d.setdefault("model", {})["template_semantic_profile"] = "internal_admin_portal"
    meta = d.setdefault("metadata", {})
    meta["tags"] = list(meta.get("tags") or []) + [
        "wz:internal_admin_portal:approval=no",
        "wz:internal_admin_portal:segregation=no",
    ]
    return ThreatModelDocument.model_validate(d)


@pytest.mark.parametrize("methodology", [m.value for m in ThreatModelMethodology])
def test_maximal_model_all_methodologies(methodology: str) -> None:
    doc = _maximal()
    res = analyze_document(doc, methodology=methodology)
    assert res.heuristic_threats is not None
    backlog = build_remediation_backlog(res, doc)
    assert backlog is not None


def test_maximal_model_aggregate_and_cockpit() -> None:
    doc = _maximal()
    res = analyze_document(doc)
    # high-risk flags should yield scored threats feeding aggregate_risk / decision_cockpit
    assert res.aggregate_risk is not None
    assert res.decision_cockpit is not None
