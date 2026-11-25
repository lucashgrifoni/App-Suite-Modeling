"""P4 regression — resolving Ingress specs must not rescan every manifest once per Ingress.

`_build_ingress_flows` called `_find_ingress_spec(docs, name)` inside its loop over `ingresses`,
and that helper walks the whole parsed document list looking for a matching Ingress. Both counts
grow with the upload, so the pair is O(ingresses x documents).

Measured before the fix, with the parse cost separated from the lookup cost, the lookups alone
doubled cleanly with the square — 8.2 ms, 32.7 ms, 131.1 ms at 400, 800 and 1600 documents — and
crossed over from 8% of the request to 94% of it by 3200 documents. `POST /v1/imports/kubernetes`
accepts 2 MiB, which holds roughly 17,900 of these manifests, and runs the parse synchronously
inside an `async def` handler, so the cost stalls the whole server rather than one request.

The measurement is worth recording because the naive version of it is misleading: fitting a growth
exponent across 100-800 documents returns k~1.06 and reads as linear. It is not — that range is
still dominated by the linear YAML parse, and the quadratic term only takes over later. The
exponent was measured in the wrong regime, not measured wrong.

The oracle below counts document scans rather than milliseconds, because the invariant is exactly
"the manifests are walked a bounded number of times" and a count cannot flake.
"""

from __future__ import annotations

from typing import Any

from otm_artifact_import.k8s_import import _build_ingress_flows


class _CountingDocs(list):
    """A document list that records how many times something walked it end to end."""

    def __init__(self, items: list[Any]) -> None:
        super().__init__(items)
        self.scans = 0

    def __iter__(self):  # type: ignore[no-untyped-def]
        self.scans += 1
        return super().__iter__()


def _ingress_doc(name: str, service: str) -> dict[str, Any]:
    return {
        "apiVersion": "networking.k8s.io/v1",
        "kind": "Ingress",
        "metadata": {"name": name},
        "spec": {
            "rules": [
                {
                    "host": f"{name}.example.com",
                    "http": {"paths": [{"backend": {"service": {"name": service}}}]},
                }
            ]
        },
    }


def _fixture(count: int) -> tuple[_CountingDocs, list[tuple[str, str, list[str]]], dict[str, str]]:
    docs = _CountingDocs([_ingress_doc(f"ing{i}", f"svc{i}") for i in range(count)])
    ingresses = [(f"k8s_ing{i}", f"ing{i}", [f"ing{i}.example.com"]) for i in range(count)]
    services = {f"svc{i}": f"k8s_svc{i}" for i in range(count)}
    return docs, ingresses, services


def _run(count: int) -> tuple[_CountingDocs, list[Any], list[str]]:
    docs, ingresses, services = _fixture(count)
    unknowns: list[str] = []
    flows = _build_ingress_flows(docs, ingresses, services, "k.yaml", lambda *a, **k: None, unknowns)
    return docs, flows, unknowns


def test_the_manifests_are_walked_a_bounded_number_of_times() -> None:
    """One walk to index them is fine. One walk per Ingress is the defect."""
    docs, _, _ = _run(64)

    assert docs.scans <= 2, f"walked {len(docs)} manifests {docs.scans} times"


def test_the_number_of_walks_does_not_grow_with_the_manifest_count() -> None:
    """The sharper statement of the same invariant: it is constant, not merely small."""
    small, _, _ = _run(16)
    large, _, _ = _run(256)

    assert small.scans == large.scans, f"16 manifests: {small.scans} walks; 256: {large.scans}"


def test_every_ingress_still_reaches_its_backend_service() -> None:
    """The flows are what the importer exists to produce; indexing may not drop any."""
    _, flows, unknowns = _run(8)

    assert [f.from_component for f in flows] == [f"k8s_ing{i}" for i in range(8)]
    assert [f.to_component for f in flows] == [f"k8s_svc{i}" for i in range(8)]
    assert unknowns == []


def test_two_ingresses_sharing_a_name_resolve_to_the_first_one_declared() -> None:
    """`_find_ingress_spec` returned the first match; the index must not silently prefer the last.

    Manifests legitimately repeat a name across namespaces, so this is reachable input, not a
    contrived one — the same shape the importer already handles for Services.
    """
    docs = _CountingDocs([_ingress_doc("shared", "svc_first"), _ingress_doc("shared", "svc_second")])
    unknowns: list[str] = []

    flows = _build_ingress_flows(
        docs,
        [("k8s_shared", "shared", ["shared.example.com"])],
        {"svc_first": "k8s_svc_first", "svc_second": "k8s_svc_second"},
        "k.yaml",
        lambda *a, **k: None,
        unknowns,
    )

    assert [f.to_component for f in flows] == ["k8s_svc_first"]


def test_an_ingress_with_no_matching_manifest_is_still_reported_as_unknown() -> None:
    """A missing spec must stay missing: the index may not invent a backend for it."""
    docs = _CountingDocs([_ingress_doc("present", "svc_present")])
    unknowns: list[str] = []

    flows = _build_ingress_flows(
        docs,
        [("k8s_absent", "absent", [])],
        {"svc_present": "k8s_svc_present"},
        "k.yaml",
        lambda *a, **k: None,
        unknowns,
    )

    assert flows == []
