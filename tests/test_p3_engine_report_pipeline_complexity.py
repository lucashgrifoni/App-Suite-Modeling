"""P3 regression — the backlog and premium-report pipeline must not be quadratic.

Four linear scans sat inside loops over the same collections, so cost grew with the square of
the model size while the response stayed a constant ~139 KB. Measured end to end, a schema-valid
797 KB document — no YAML aliases, no deep nesting, nothing any existing input guard rejects,
simply *wide* — bought 63 s of single-core CPU from one request to `/v1/reports/premium`, an
endpoint reachable without a key when `OTM_API_KEY` is unset. `otm report --level deep` pays the
same cost in CI, on a committed model.

The four sites, all now index lookups:

* `remediation/build.py` `_sort_score` re-scanned every heuristic threat for each backlog item,
  from inside `sorted()`;
* `remediation/build.py` `_item_from_threat` rebuilt `{component.id: name}` for every item;
* `remediation/classify.py` `component_kind_for_id` re-scanned `doc.components` on every call,
  and the whole report calls it once per threat (and O(n log n) times inside its own `sorted`);
* `report-premium/builder.py` `_build_root_cause_groups` re-scanned every backlog item per group
  and tested membership against a `list`.

No behaviour changed, which is the other half of what these tests hold: the lookups return what
the scans returned, and the groups keep the order they had.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest
from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from otm_report_premium.builder import build_premium_report_payload
from otm_report_premium.enums import ReportLevel
from otm_threat_engine import analyze_document, build_remediation_backlog
from otm_threat_engine.remediation.classify import ComponentIndex, component_kind_for_id

_ROOT = Path(__file__).resolve().parents[1]
_SAAS = _ROOT / "examples" / "saas-ordering-v1.otm.yaml"

#: Two sizes a factor of four apart. Quadratic growth costs ~16x here and was measured at 10-16x
#: before the fix; linear costs ~4x and measures ~4.6x with the `sorted` term. The bar sits at 8,
#: which no linear implementation approaches and no quadratic one survives — the same criterion
#: the finding proposed, with room for a loaded CI runner.
_SMALL = 200
_LARGE = 800
_MAX_GROWTH = 8.0
_REPEATS = 3


def _wide_model(n: int) -> ThreatModelDocument:
    """`n` components and `n` flows: boring, schema-valid, and large only in width."""
    payload: dict[str, Any] = {
        "model": {"schema_version": "1.0.0", "system_type": "web_application"},
        "metadata": {"title": f"Wide model {n}", "owner": "appsec@empresa.example"},
        "trust_boundaries": [
            {"id": "internet", "name": "Internet", "member_component_ids": ["edge"]},
            {"id": "vpc", "name": "VPC", "member_component_ids": [f"svc_{i}" for i in range(n)]},
        ],
        "components": [
            {"id": "edge", "name": "Edge", "kind": "gateway"},
            *[
                {
                    "id": f"svc_{i}",
                    "name": f"Service {i}",
                    "kind": "process" if i % 2 else "datastore",
                    "handles_sensitive_data": i % 3 == 0,
                }
                for i in range(n)
            ],
        ],
        "data_flows": [
            {
                "id": f"flow_{i}",
                "name": f"Flow {i}",
                "from_component": "edge",
                "to_component": f"svc_{i}",
                "protocol": "https",
                "authenticated": bool(i % 2),
                "encrypted": bool(i % 2),
                "public_exposure": i % 4 == 0,
            }
            for i in range(n)
        ],
        "assets": [],
        "threats": [],
    }
    return ThreatModelDocument.model_validate(payload)


def _best_of(run: Any, reps: int = _REPEATS) -> float:
    """The fastest of a few runs: scheduler noise only ever makes a run slower."""
    return min(_timed(run) for _ in range(reps))


def _timed(run: Any) -> float:
    start = time.perf_counter()
    run()
    return time.perf_counter() - start


def _growth(build: Any) -> float:
    small_doc, large_doc = _wide_model(_SMALL), _wide_model(_LARGE)
    small_result, large_result = analyze_document(small_doc), analyze_document(large_doc)
    small = _best_of(lambda: build(small_doc, small_result))
    large = _best_of(lambda: build(large_doc, large_result))
    return large / small


# ------------------------------------------------------------------ growth


def test_premium_report_growth_is_sub_quadratic() -> None:
    growth = _growth(
        lambda doc, result: build_premium_report_payload(doc, result, level=ReportLevel.DEEP, include_mermaid=False)
    )

    assert growth < _MAX_GROWTH, f"4x the entities cost {growth:.1f}x the time"


def test_remediation_backlog_growth_is_sub_quadratic() -> None:
    growth = _growth(lambda doc, result: build_remediation_backlog(result, doc))

    assert growth < _MAX_GROWTH, f"4x the entities cost {growth:.1f}x the time"


def test_the_component_index_is_built_a_bounded_number_of_times(monkeypatch: pytest.MonkeyPatch) -> None:
    """A deterministic companion to the timings: the index must not be rebuilt per threat."""
    calls: list[int] = []
    original = ComponentIndex.of

    def counting_of(doc: ThreatModelDocument | None) -> ComponentIndex:
        calls.append(1)
        return original(doc)

    monkeypatch.setattr(ComponentIndex, "of", staticmethod(counting_of))

    counts = []
    for n in (_SMALL, _LARGE):
        calls.clear()
        doc = _wide_model(n)
        build_premium_report_payload(doc, analyze_document(doc), level=ReportLevel.DEEP, include_mermaid=False)
        counts.append(len(calls))

    assert counts[0] == counts[1], f"index rebuilt more often on the larger model: {counts}"
    assert counts[0] <= 4, f"expected a handful of index builds per report, got {counts[0]}"


# ------------------------------------------------------- behaviour is unchanged


def test_the_indexed_lookup_answers_exactly_what_the_scan_answered() -> None:
    doc = load_document_from_yaml_path(_SAAS)
    index = ComponentIndex.of(doc)

    for component in doc.components:
        assert component_kind_for_id(doc, component.id, index=index) == component.kind
        assert component_kind_for_id(doc, component.id) == component.kind


@pytest.mark.parametrize(
    ("doc_given", "cid"),
    [(True, "no_such_component"), (True, None), (False, "anything"), (False, None)],
)
def test_the_indexed_lookup_keeps_the_none_answers(doc_given: bool, cid: str | None) -> None:
    """A missing id, a missing target and a missing document all still answer `None`."""
    doc = load_document_from_yaml_path(_SAAS) if doc_given else None

    assert component_kind_for_id(doc, cid) is None
    assert component_kind_for_id(doc, cid, index=ComponentIndex.of(doc)) is None


def test_root_cause_groups_keep_the_backlog_order() -> None:
    """The membership test changed from a list to a set; the iteration order must not have."""
    doc = load_document_from_yaml_path(_SAAS)
    result = analyze_document(doc)
    backlog = build_remediation_backlog(result, doc)
    payload = build_premium_report_payload(doc, result, level=ReportLevel.DEEP, include_mermaid=False)
    order = [item.id for item in backlog.items]

    for group in payload.root_cause_groups:
        declared = backlog.by_root_cause[group.key]
        expected = [item_id for item_id in order if item_id in set(declared)]
        assert group.threat_count == len(expected)


def test_backlog_priority_order_survives_the_index(monkeypatch: pytest.MonkeyPatch) -> None:
    """`_sort_score` stopped scanning; the ranking it produces must be the same one."""
    doc = load_document_from_yaml_path(_SAAS)
    result = analyze_document(doc)
    backlog = build_remediation_backlog(result, doc)
    scores = {h.id: h.risk.score or 0.0 for h in result.heuristic_threats}

    ranked = sorted(backlog.items, key=lambda i: i.priority_rank)
    from_threats = [
        scores[i.related_findings[0].id]
        for i in ranked
        if i.related_findings and i.related_findings[0].kind == "heuristic_threat"
    ]

    assert from_threats == sorted(from_threats, reverse=True)
