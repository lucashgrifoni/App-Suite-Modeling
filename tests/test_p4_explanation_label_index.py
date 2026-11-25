"""P4 regression — building explanations must not rescan the model once per threat.

`_comp_label` walked `doc.components` and `_asset_note` walked `doc.assets` on every call, and
`merge_analysis_explanations` calls both once per heuristic threat. The threat count grows with the
entity count, so the pair cost O(entities x threats).

Profiled on the wide model, `_comp_label` alone took 3.0 ms at 300 entities, 12.2 ms at 600 and
43.3 ms at 1200 — 4.1x then 3.5x per doubling, which is the square. For contrast the same profile
put `refs_for_stride` at 154 ms, far larger today, but growing 2.6x then 1.8x: linear, a constant
factor rather than a shape. The quadratic one is the one that overtakes, at around 4000 entities,
and keeps going; the constant one is a separate question about defensive copying and is left alone.

The oracle counts walks of the document's own lists rather than milliseconds, so it states the
invariant directly — "the model is indexed, not rescanned" — and cannot flake on a loaded runner.
"""

from __future__ import annotations

from typing import Any

from otm_core_schema import ThreatModelDocument
from otm_threat_engine import analyze_document
from otm_threat_engine.explanation_builders import _asset_note, _comp_label, merge_analysis_explanations


class _CountingList(list):
    """Records how many times something walked it end to end."""

    def __init__(self, items: list[Any]) -> None:
        super().__init__(items)
        self.scans = 0

    def __iter__(self):  # type: ignore[no-untyped-def]
        self.scans += 1
        return super().__iter__()


def _model(entities: int) -> ThreatModelDocument:
    payload: dict[str, Any] = {
        "model": {"schema_version": "1.0.0", "system_type": "web_application"},
        "metadata": {"title": "Label index", "owner": "appsec@empresa.example"},
        "trust_boundaries": [
            {"id": "vpc", "name": "VPC", "member_component_ids": [f"svc_{i}" for i in range(entities)]}
        ],
        "components": [
            {"id": f"svc_{i}", "name": f"Service {i}", "kind": "process" if i % 2 else "datastore"}
            for i in range(entities)
        ],
        "data_flows": [
            {
                "id": f"flow_{i}",
                "name": f"Flow {i}",
                "from_component": "svc_0",
                "to_component": f"svc_{i}",
                "protocol": "https",
                "authenticated": bool(i % 2),
                "encrypted": bool(i % 2),
            }
            for i in range(1, entities)
        ],
        "assets": [{"id": f"asset_{i}", "name": f"Asset {i}", "sensitivity": "critical"} for i in range(entities)],
        "threats": [],
    }
    return ThreatModelDocument.model_validate(payload)


def _walks(entities: int) -> tuple[int, int, int]:
    """Returns (component walks, asset walks, explanations produced) for one merge."""
    doc = _model(entities)
    result = analyze_document(doc)
    doc.components = _CountingList(doc.components)
    doc.assets = _CountingList(doc.assets)

    records = merge_analysis_explanations(doc, result)

    return doc.components.scans, doc.assets.scans, len(records)


def test_the_components_are_walked_a_bounded_number_of_times() -> None:
    """Three full passes, and every one of them is traced to a caller that runs exactly once.

    Two belong to `resolve_component_boundaries` (`trust_membership.py:25` and `:33`), reached once
    through `cross_boundary_flow_ids`; the third builds the label index. None is per-threat, which
    is the whole claim — before the index there were 42 passes at 10 entities and 242 at 60.
    """
    component_walks, _, records = _walks(40)

    assert records > 0, "the fixture must actually produce explanations, or this proves nothing"
    assert component_walks <= 3, f"{records} explanations walked the component list {component_walks} times"


def test_the_assets_are_walked_a_bounded_number_of_times() -> None:
    _, asset_walks, records = _walks(40)

    assert records > 0
    assert asset_walks <= 2, f"{records} explanations walked the asset list {asset_walks} times"


def test_the_number_of_walks_does_not_grow_with_the_model() -> None:
    """The sharper statement: constant, not merely small."""
    small_components, small_assets, _ = _walks(10)
    large_components, large_assets, _ = _walks(60)

    assert small_components == large_components, f"10 entities: {small_components}; 60: {large_components}"
    assert small_assets == large_assets, f"10 entities: {small_assets}; 60: {large_assets}"


def test_the_explanations_are_unchanged_by_indexing() -> None:
    """Behaviour lock: the records a reader sees must be identical, field for field."""
    doc = _model(12)
    result = analyze_document(doc)

    records = merge_analysis_explanations(doc, result)

    assert records
    assert [r.model_dump() for r in records] == [r.model_dump() for r in merge_analysis_explanations(doc, result)]
    assert any("Service 1 (svc_1)" in " ".join(r.evidence) for r in records), "the component label must still appear"


def test_the_label_helpers_keep_their_direct_contract() -> None:
    """These two are called directly elsewhere; an index must not change what they answer."""
    doc = _model(3)

    assert _comp_label(doc, None) is None
    assert _comp_label(doc, "svc_1") == "Service 1 (svc_1)"
    assert _comp_label(doc, "ghost") == "ghost"
    assert _asset_note(doc, None) is None
    assert _asset_note(doc, "asset_1") == "ativo Asset 1 — critical"
    assert _asset_note(doc, "ghost") is None
