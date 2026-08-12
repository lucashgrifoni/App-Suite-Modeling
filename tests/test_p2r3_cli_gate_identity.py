"""Round-3 regression: what makes two analyses "the same system" for an armed CI gate.

Round 2 taught `otm diff-analysis` to refuse a pair of analyses describing *different* systems,
because the gate would otherwise blame a PR for the other model's threats. It identified the
system by `document_title` — and a title is user-facing prose that people legitimately rewrite.
Renaming `metadata.title` on an otherwise untouched model therefore hard-failed an armed gate
with a "two different systems" error, and that error *replaced* the verdict: a PR that renamed
the model and made it worse in the same commit exited 1 with a misleading message instead of
exiting 3 with the regression it had actually introduced.

Identity now comes from the structural shape the threats are derived from — the entities they
target plus the trust boundaries the flows cross. A rename leaves that untouched; a different
system does not produce it. Entity ids alone are too weak (the template catalog hands out `api`,
`db`, `user`, so unrelated models collide on a handful), which is why the guard asks for a
*proportion* of the smaller shape rather than a shared id, and why the boundary wiring is part of
the shape.

Exit-code contract: 0 = no trip, 1 = usage error/refusal, 3 = gate tripped.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from click.testing import Result
from otm_cli.cli import app
from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from otm_threat_engine import analyze_document
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"
_SAAS = _ROOT / "examples" / "saas-ordering-v1.otm.yaml"

_GATE_TRIP = 3
_USAGE_ERROR = 1

#: A schema-valid model that declares no components and no flows, so its analysis carries no
#: structural shape at all. Nothing can be concluded from it either way.
_STRUCTURELESS: dict[str, Any] = {
    "model": {"schema_version": "1.0.0", "system_type": "web_application"},
    "metadata": {"title": "Structureless stub", "owner": "appsec@empresa.example"},
}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _out(result: Result) -> str:
    return (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")


def _saas() -> dict[str, Any]:
    """The reference model as a plain dict, so a test can edit it the way a maintainer would."""
    return yaml.safe_load(_SAAS.read_text(encoding="utf-8"))


def _store_dict(document: dict[str, Any], target: Path) -> Path:
    result = analyze_document(ThreatModelDocument.model_validate(document))
    target.write_text(json.dumps(result.model_dump(mode="json")), encoding="utf-8")
    return target


def _store_file(model: Path, target: Path) -> Path:
    result = analyze_document(load_document_from_yaml_path(model))
    target.write_text(json.dumps(result.model_dump(mode="json")), encoding="utf-8")
    return target


@pytest.fixture
def baseline(tmp_path: Path) -> Path:
    return _store_dict(_saas(), tmp_path / "baseline.json")


# --- a rename is not a change of system --------------------------------------------------------


def test_a_title_rename_no_longer_refuses_an_armed_gate(runner: CliRunner, baseline: Path, tmp_path: Path) -> None:
    """The reproduction: same model, `metadata.title` edited, armed gate — used to exit 1."""
    renamed = _saas()
    renamed["metadata"]["title"] = "Ordering Platform (renamed)"
    revised = _store_dict(renamed, tmp_path / "renamed.json")

    result = runner.invoke(app, ["diff-analysis", str(baseline), str(revised), "--fail-on", "medium"])

    assert result.exit_code == 0


def test_a_title_rename_is_not_reported_as_two_systems(runner: CliRunner, baseline: Path, tmp_path: Path) -> None:
    renamed = _saas()
    renamed["metadata"]["title"] = "Ordering Platform (renamed)"
    revised = _store_dict(renamed, tmp_path / "renamed.json")

    result = runner.invoke(app, ["diff-analysis", str(baseline), str(revised), "--fail-on", "medium"])

    assert "two different systems" not in _out(result)


def test_a_description_edit_no_longer_refuses_an_armed_gate(runner: CliRunner, baseline: Path, tmp_path: Path) -> None:
    """Prose the gate has no business reading: summary and business description."""
    edited = _saas()
    edited["metadata"]["summary"] = "Reescrito: web, API, workers e base de dados."
    edited["business_context"]["description"] = "Descrição reescrita do contexto de negócio."
    revised = _store_dict(edited, tmp_path / "edited.json")

    result = runner.invoke(app, ["diff-analysis", str(baseline), str(revised), "--fail-on", "medium"])

    assert result.exit_code == 0


# --- the refusal must never stand in for a verdict ---------------------------------------------


@pytest.fixture
def renamed_and_worse(tmp_path: Path) -> Path:
    """One commit that renames the model *and* drops auth+encryption on `waf_to_api`.

    Max score rises 20 -> 25. The round-2 guard reported "different documents" and exited 1,
    hiding the regression behind a mismatch error nobody could act on.
    """
    worse = _saas()
    worse["metadata"]["title"] = "Ordering Platform (renamed)"
    for flow in worse["data_flows"]:
        if flow["id"] == "waf_to_api":
            flow["authenticated"] = False
            flow["encrypted"] = False
    return _store_dict(worse, tmp_path / "renamed_and_worse.json")


def test_a_renamed_model_that_got_worse_still_trips_the_gate(
    runner: CliRunner, baseline: Path, renamed_and_worse: Path
) -> None:
    result = runner.invoke(app, ["diff-analysis", str(baseline), str(renamed_and_worse), "--fail-on", "high"])

    assert result.exit_code == _GATE_TRIP


def test_a_rename_never_masks_a_risk_increase(runner: CliRunner, baseline: Path, renamed_and_worse: Path) -> None:
    """The `--fail-on-risk-increase` direction of the same masking bug."""
    result = runner.invoke(app, ["diff-analysis", str(baseline), str(renamed_and_worse), "--fail-on-risk-increase"])

    assert result.exit_code == _GATE_TRIP


# --- a different system is still refused -------------------------------------------------------


@pytest.fixture
def different_systems(tmp_path: Path) -> tuple[Path, Path]:
    return (
        _store_file(_MINIMAL, tmp_path / "minimal.json"),
        _store_file(_SAAS, tmp_path / "saas.json"),
    )


def test_an_armed_gate_still_refuses_two_completely_different_systems(
    runner: CliRunner, different_systems: tuple[Path, Path]
) -> None:
    """The round-2 bug's real case, which the new signal must keep refusing."""
    minimal, saas = different_systems

    result = runner.invoke(app, ["diff-analysis", str(minimal), str(saas), "--fail-on", "high"])

    assert result.exit_code == _USAGE_ERROR


def test_the_refusal_reports_how_much_shape_the_two_share(
    runner: CliRunner, different_systems: tuple[Path, Path]
) -> None:
    """A maintainer must be able to tell a real mismatch from an over-eager guard."""
    minimal, saas = different_systems

    result = runner.invoke(app, ["diff-analysis", str(minimal), str(saas), "--fail-on", "high"])

    assert "structural" in _out(result)


# --- a growing model is the same system --------------------------------------------------------


def test_a_model_that_doubled_in_size_is_still_the_same_system(
    runner: CliRunner, baseline: Path, tmp_path: Path
) -> None:
    """Adding components is the normal case an armed gate exists to judge, not a new system.

    A symmetric similarity measure fails here: doubling the model drops it below every threshold
    that still separates two different systems.
    """
    grown = _saas()
    for i in range(12):
        grown["components"].append(
            {"id": f"svc{i}", "name": f"Serviço {i}", "kind": "process", "in_trust_boundary": "app_tier"}
        )
        grown["data_flows"].append(
            {"id": f"api_to_svc{i}", "from_component": "api", "to_component": f"svc{i}", "protocol": "HTTPS"}
        )
    revised = _store_dict(grown, tmp_path / "grown.json")

    result = runner.invoke(app, ["diff-analysis", str(baseline), str(revised), "--fail-on", "medium"])

    assert result.exit_code != _USAGE_ERROR


# --- no shape is no evidence -------------------------------------------------------------------


def test_two_analyses_without_any_shape_are_not_refused(runner: CliRunner, tmp_path: Path) -> None:
    """A model with no components has no shape; refusing would hide the diff on no evidence."""
    left = _store_dict(_STRUCTURELESS, tmp_path / "left.json")
    right = _store_dict(_STRUCTURELESS, tmp_path / "right.json")

    result = runner.invoke(app, ["diff-analysis", str(left), str(right), "--fail-on", "low"])

    assert result.exit_code == 0


def test_a_shapeless_baseline_is_not_refused_against_a_modelled_one(
    runner: CliRunner, baseline: Path, tmp_path: Path
) -> None:
    """Growing a stub into a real model must reach the gate, not a mismatch error."""
    stub = _store_dict(_STRUCTURELESS, tmp_path / "stub.json")

    result = runner.invoke(app, ["diff-analysis", str(stub), str(baseline), "--fail-on", "medium"])

    assert result.exit_code != _USAGE_ERROR


def test_boundary_findings_without_ids_contribute_no_shared_shape(
    runner: CliRunner, different_systems: tuple[Path, Path], tmp_path: Path
) -> None:
    """A hand-edited or older artifact can carry a crossing that names no boundaries.

    Two unrelated models must not be judged the same system because both record the same
    *absence*; the guard has to ignore such a finding rather than fold `None` into the shape.
    """
    minimal, saas = different_systems
    blank = {"code": "CROSS_BOUNDARY_FLOW", "message": "boundary ids lost"}
    patched: list[Path] = []
    for source in (minimal, saas):
        payload = json.loads(source.read_text(encoding="utf-8"))
        payload["trust_boundary_findings"] = [blank]
        target = tmp_path / f"blank_{source.name}"
        target.write_text(json.dumps(payload), encoding="utf-8")
        patched.append(target)

    result = runner.invoke(app, ["diff-analysis", str(patched[0]), str(patched[1]), "--fail-on", "high"])

    assert result.exit_code == _USAGE_ERROR


# --- the other provenance guards are untouched -------------------------------------------------


def test_the_same_model_analysed_twice_still_gates_cleanly(runner: CliRunner, baseline: Path, tmp_path: Path) -> None:
    """The setup CI actually uses: identical model both sides, armed gate, nothing to report."""
    revised = _store_dict(_saas(), tmp_path / "revised.json")

    result = runner.invoke(app, ["diff-analysis", str(baseline), str(revised), "--fail-on", "low"])

    assert result.exit_code == 0


def test_a_renamed_model_is_still_refused_across_engine_versions(
    runner: CliRunner, baseline: Path, tmp_path: Path
) -> None:
    """Structural identity must not disarm the guard that was already correct."""
    renamed = _saas()
    renamed["metadata"]["title"] = "Ordering Platform (renamed)"
    revised = _store_dict(renamed, tmp_path / "renamed.json")
    payload = json.loads(revised.read_text(encoding="utf-8"))
    payload["engine_version"] = "99.0.0"
    revised.write_text(json.dumps(payload), encoding="utf-8")

    result = runner.invoke(app, ["diff-analysis", str(baseline), str(revised), "--fail-on", "medium"])

    assert result.exit_code == _USAGE_ERROR
