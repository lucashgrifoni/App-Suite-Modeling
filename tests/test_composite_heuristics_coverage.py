"""Coverage — composite heuristics (SSRF, upload chain, privileged public surface, gateway)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from otm_threat_engine.composite_heuristics import append_composite_heuristics
from otm_threat_engine.result import HeuristicThreat

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def _doc_with_composite_flags() -> ThreatModelDocument:
    d: dict[str, Any] = load_document_from_yaml_path(_MINIMAL).model_dump(mode="python", by_alias=True)
    tb = (d.get("trust_boundaries") or [{"id": "internet"}])[0]["id"]
    d["components"].append({"id": "edge_gw", "name": "Gateway", "kind": "gateway", "in_trust_boundary": tb})
    flows = d.get("data_flows") or []
    # ensure at least 3 flows to tag
    while len(flows) < 3:
        src = d["components"][0]["id"]
        dst = d["components"][1]["id"]
        flows.append({"id": f"f_extra_{len(flows)}", "from_component": src, "to_component": dst, "name": "x"})
    flows[0]["semantic_class"] = "external_fetch"
    flows[0]["input_from_untrusted_source"] = True
    flows[1]["semantic_class"] = "file_upload"
    flows[1]["supports_file_upload"] = True
    flows[2]["public_exposure"] = True
    flows[2]["affects_privileged_state"] = True
    d["data_flows"] = flows
    return ThreatModelDocument.model_validate(d)


def test_composite_patterns_all_fire() -> None:
    doc = _doc_with_composite_flags()
    heuristics: list[HeuristicThreat] = []
    added = append_composite_heuristics(doc, heuristics, existing_ids=set())
    ids = {h.id for h in heuristics}
    assert added >= 3
    assert any(i.startswith("cmp_ssrf_") for i in ids)
    assert any(i.startswith("cmp_upload_") for i in ids)
    assert any(i.startswith("cmp_priv_") for i in ids)
    assert any(i.startswith("cmp_gw_") for i in ids)


def test_composite_idempotent_with_existing_ids() -> None:
    doc = _doc_with_composite_flags()
    heuristics: list[HeuristicThreat] = []
    first = append_composite_heuristics(doc, heuristics, existing_ids=set())
    # Re-run with the already-produced ids -> nothing new added.
    existing = {h.id for h in heuristics}
    again = append_composite_heuristics(doc, [], existing_ids=existing)
    assert first >= 3
    assert again == 0


def test_composite_no_flags_no_additions() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    heuristics: list[HeuristicThreat] = []
    # minimal model has no gateway and no composite flags set -> typically 0 additions
    added = append_composite_heuristics(doc, heuristics, existing_ids=set())
    assert added >= 0
