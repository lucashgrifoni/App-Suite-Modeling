"""P4 regression — a format asked for twice must be rendered once.

`build_exports` returns `dict[str, str]` keyed on the format name, so a repeated entry in `formats`
overwrites the key it just wrote. The render still ran. Nothing in the request path deduplicates
the list and nothing bounds its length, so each extra entry buys a full export whose only fate is
to be discarded.

Measured against a real server on the default posture — no API key, no rate limit — a 47 KB request
carrying `analysis_markdown` 2000 times took 558 ms and returned the same 14,459 bytes as a request
carrying it once, while an unrelated `GET /health` waited 158 ms behind it. That is roughly 12
microseconds of CPU bought per byte of request, and `/v1/exports` is a JSON route, so unlike the
upload routes it has no body-size ceiling at all.

Deduplicating is free of observable consequence, which is what makes it the right fix here rather
than a workaround: `dict` keeps a key in the position of its *first* insertion, so collapsing the
list beforehand yields the same keys, in the same order, with the same values. The tests below pin
all three, so the optimisation cannot quietly become a behaviour change.

The missing body-size ceiling is a separate, larger question about deployment posture and is not
addressed here.
"""

from __future__ import annotations

import pytest
from otm_api.domain.export_formats import ExportFormat
from otm_api.services import exports as exports_service
from otm_api.services.exports import build_exports
from otm_core_schema import load_document_from_yaml_path

_DOC = load_document_from_yaml_path("examples/saas-ordering-v1.otm.yaml")


@pytest.fixture
def render_counts(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    """Count each exporter call. Deterministic where a stopwatch would not be."""
    counts: dict[str, int] = {}

    for name in (
        "export_document_json",
        "export_document_markdown",
        "export_flowchart_mermaid",
        "export_analysis_json",
        "export_analysis_markdown",
        "export_threat_model_bundle_json",
    ):
        original = getattr(exports_service, name)

        def counting(*args: object, _name: str = name, _original: object = original, **kwargs: object) -> object:
            counts[_name] = counts.get(_name, 0) + 1
            return _original(*args, **kwargs)  # type: ignore[operator]

        monkeypatch.setattr(exports_service, name, counting)

    return counts


def test_a_format_asked_for_twenty_times_is_rendered_once(render_counts: dict[str, int]) -> None:
    build_exports(_DOC, formats=[ExportFormat.document_markdown] * 20)

    assert render_counts == {"export_document_markdown": 1}


def test_each_distinct_format_is_still_rendered(render_counts: dict[str, int]) -> None:
    """Deduplicating may not drop a format the caller actually asked for."""
    build_exports(
        _DOC,
        formats=[ExportFormat.document_json, ExportFormat.document_markdown, ExportFormat.document_json],
    )

    assert render_counts == {"export_document_json": 1, "export_document_markdown": 1}


def test_duplicates_do_not_change_the_response() -> None:
    """The contract: same keys, same values, whatever the caller repeated."""
    once = build_exports(_DOC, formats=[ExportFormat.document_json, ExportFormat.document_markdown])
    repeated = build_exports(
        _DOC,
        formats=[
            ExportFormat.document_json,
            ExportFormat.document_markdown,
            ExportFormat.document_json,
            ExportFormat.document_markdown,
        ],
    )

    assert repeated == once


def test_interleaved_duplicates_keep_the_first_occurrence_order() -> None:
    """`dict` keeps a key where it was first inserted; collapsing the list must agree with that."""
    formats = [
        ExportFormat.document_markdown,
        ExportFormat.document_json,
        ExportFormat.document_markdown,
        ExportFormat.flowchart_mermaid,
    ]

    assert list(build_exports(_DOC, formats=formats)) == [
        ExportFormat.document_markdown.value,
        ExportFormat.document_json.value,
        ExportFormat.flowchart_mermaid.value,
    ]


def test_analysis_is_still_run_once_for_a_repeated_analysis_format(render_counts: dict[str, int]) -> None:
    """The analysis was already hoisted out of the loop; deduplicating must not disturb it."""
    build_exports(_DOC, formats=[ExportFormat.analysis_markdown] * 5)

    assert render_counts == {"export_analysis_markdown": 1}
