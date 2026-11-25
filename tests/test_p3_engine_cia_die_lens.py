"""P3 security regression — the `cia_die` lens must not truncate the analysis it hands the gate.

`_apply_cia_die_lens` used to keep the ten highest-scoring active threats and rebuild
`heuristic_threats` from that selection. It was the only lens that removed rather than added,
and `recompute_summary_with_methodology` then recounted the summary over the truncated list, so
the result no longer recorded that anything had been dropped.

That is a gate that lies. `cia_die` is a first-class methodology in the CLI, the API and the UI,
and is also selectable from inside the model file via `model.methodology`. With both sides of a
diff on the same lens, `AnalysisDiff.methodology_changed` is False and the fail-closed path in
`gate.evaluate_gate` never runs — so a PR introducing new HIGH threats past the tenth exited 0
with "No new or worsened threats at or above the threshold". The same truncation emptied the
SARIF upload, the premium report, the remediation backlog and the risk cockpit.

Selecting the ten of highest impact for an executive read-out is legitimate *presentation*, and
it is still done — as a `methodology_insights` block, which the Markdown exporter and the web UI
already render. What is not legitimate is expressing that selection by deleting the analysis.

The tests below pin both directions: nothing is hidden any more (`_hides_nothing`), and the lens
did not become a source of spurious failures either (`_does_not_over_report`).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml
from otm_cli.cli import app
from otm_core_schema import ThreatModelDocument, ThreatModelMethodology, load_document_from_yaml_path
from otm_threat_engine import analyze_document
from otm_threat_engine.methodology_lenses.dispatch import CIA_DIE_HIGHLIGHT_COUNT
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_SAAS = _ROOT / "examples" / "saas-ordering-v1.otm.yaml"
_GATE_TRIP = 3


@pytest.fixture
def saas_doc() -> ThreatModelDocument:
    return load_document_from_yaml_path(_SAAS)


def _write(path: Path, payload: dict[str, object]) -> Path:
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def _base_and_head(tmp_path: Path) -> tuple[Path, Path]:
    """A PR that adds one sensitive datastore — three new HIGH heuristics under any lens."""
    base_payload = yaml.safe_load(_SAAS.read_text(encoding="utf-8"))
    head_payload = copy.deepcopy(base_payload)
    head_payload["components"].append(
        {"id": "pii_export_store", "name": "PII export store", "kind": "datastore", "handles_sensitive_data": True}
    )
    return (
        _write(tmp_path / "base.otm.yaml", base_payload),
        _write(tmp_path / "head.otm.yaml", head_payload),
    )


# --------------------------------------------------------------- the lens hides nothing


def test_cia_die_keeps_every_heuristic_stride_produces(saas_doc: ThreatModelDocument) -> None:
    under_stride = analyze_document(saas_doc, methodology=ThreatModelMethodology.STRIDE)
    under_cia_die = analyze_document(saas_doc, methodology=ThreatModelMethodology.CIA_DIE)

    assert [h.id for h in under_cia_die.heuristic_threats] == [h.id for h in under_stride.heuristic_threats]


def test_cia_die_summary_describes_the_analysis_and_not_the_selection(saas_doc: ThreatModelDocument) -> None:
    """The truncation also rewrote the counters, so the loss was invisible in the output."""
    under_stride = analyze_document(saas_doc, methodology=ThreatModelMethodology.STRIDE)
    under_cia_die = analyze_document(saas_doc, methodology=ThreatModelMethodology.CIA_DIE)

    assert under_cia_die.summary.heuristic_threats_generated == under_stride.summary.heuristic_threats_generated
    assert under_cia_die.summary.max_risk_score == under_stride.summary.max_risk_score


def test_the_armed_gate_sees_the_new_high_threats_under_cia_die(tmp_path: Path) -> None:
    """The bypass itself: same PR, same threshold, `-m cia_die` used to exit 0."""
    base, head = _base_and_head(tmp_path)
    runner = CliRunner()

    under_stride = runner.invoke(
        app, ["diff", str(base), str(head), "--with-analysis", "-m", "stride", "--fail-on", "high"]
    )
    under_cia_die = runner.invoke(
        app, ["diff", str(base), str(head), "--with-analysis", "-m", "cia_die", "--fail-on", "high"]
    )

    assert under_stride.exit_code == _GATE_TRIP, under_stride.output
    assert under_cia_die.exit_code == _GATE_TRIP, under_cia_die.output


def test_the_gate_report_names_the_new_threats_under_cia_die(tmp_path: Path) -> None:
    base, head = _base_and_head(tmp_path)

    report = CliRunner().invoke(
        app, ["diff", str(base), str(head), "--with-analysis", "-m", "cia_die", "--fail-on", "high"]
    )

    assert "eng_pii_export_store_information_disclosure" in report.output.replace("\n", "")


def test_the_sarif_export_carries_every_threat_under_cia_die(tmp_path: Path, saas_doc: ThreatModelDocument) -> None:
    """SARIF identity is the threat id; dropping results reads as alerts being resolved."""
    sarif_out = tmp_path / "cia.sarif"

    run = CliRunner().invoke(app, ["analyze", str(_SAAS), "-m", "cia_die", "--sarif-out", str(sarif_out), "-q"])

    assert run.exit_code == 0, run.output
    under_stride = analyze_document(saas_doc, methodology=ThreatModelMethodology.STRIDE)
    expected = sum(1 for h in under_stride.heuristic_threats if not h.skipped_as_duplicate)
    exported = json.loads(sarif_out.read_text(encoding="utf-8"))["runs"][0]["results"]
    assert len(exported) == expected


# ------------------------------------------------- the executive selection is still made


def test_the_executive_highlight_block_replaces_the_truncation(saas_doc: ThreatModelDocument) -> None:
    result = analyze_document(saas_doc, methodology=ThreatModelMethodology.CIA_DIE)
    active = [h for h in result.heuristic_threats if not h.skipped_as_duplicate]
    assert len(active) > CIA_DIE_HIGHLIGHT_COUNT  # otherwise this fixture proves nothing

    block = result.methodology_insights.blocks[0] if result.methodology_insights else None

    assert block is not None
    assert block.key == "cia_die_top_impact"
    assert len(block.items) == CIA_DIE_HIGHLIGHT_COUNT


def test_the_highlight_block_lists_the_highest_scoring_threats(saas_doc: ThreatModelDocument) -> None:
    result = analyze_document(saas_doc, methodology=ThreatModelMethodology.CIA_DIE)
    active = [h for h in result.heuristic_threats if not h.skipped_as_duplicate]
    top_scores = sorted((h.risk.score or 0.0 for h in active), reverse=True)[:CIA_DIE_HIGHLIGHT_COUNT]

    items = result.methodology_insights.blocks[0].items if result.methodology_insights else []

    assert [float(line.split("]")[0].lstrip("[")) for line in items] == top_scores


# ----------------------------------------- and the lens did not start over-reporting


def test_an_unchanged_model_still_passes_the_armed_gate_under_cia_die(tmp_path: Path) -> None:
    """Lesson from this campaign: a fix against false accepts must not create false refusals."""
    base, _head = _base_and_head(tmp_path)

    run = CliRunner().invoke(
        app, ["diff", str(base), str(base), "--with-analysis", "-m", "cia_die", "--fail-on", "low"]
    )

    assert run.exit_code == 0, run.output


def test_a_removal_only_change_still_passes_under_cia_die(tmp_path: Path) -> None:
    """Removals never trip by design; keeping every threat must not have changed that."""
    base, head = _base_and_head(tmp_path)

    run = CliRunner().invoke(
        app, ["diff", str(head), str(base), "--with-analysis", "-m", "cia_die", "--fail-on", "low"]
    )

    assert run.exit_code == 0, run.output


def test_cia_die_analysis_still_pairs_with_its_own_document(saas_doc: ThreatModelDocument) -> None:
    """The identity guards used to exempt `cia_die`; without truncation they must simply pass."""
    from otm_threat_engine.analysis_identity import foreign_entity_ids, unanalysed_component_ids

    analysis = analyze_document(saas_doc, methodology=ThreatModelMethodology.CIA_DIE)

    assert unanalysed_component_ids(saas_doc, analysis) == []
    assert foreign_entity_ids(saas_doc, analysis) == []
