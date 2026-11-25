"""Round-2 regressions: what `otm diff-analysis` is allowed to issue a CI verdict about.

`diff-analysis` already refused to gate two analyses produced by different **engine versions**,
with the right reasoning: heuristics differ, so new or worsened threats cannot be attributed to
the model change. Two other recorded inputs shape the same heuristic set and were never compared.

* **The industry pack.** Gating a no-pack baseline against a `-p finance` revision of the *same,
  unchanged* model reported 5 new CRITICAL/HIGH threats and 6 worsened ones and exited 3 — a red
  build for a change nobody made. Worse in the other direction: with the pack on the baseline
  side, its score inflation exactly cancelled a real `12 -> 15` regression and the gate reported
  PASSED, exit 0. A CI gate answering "did this change make the model worse?" said no when the
  answer was yes.

* **The system itself.** Two analyses of *completely different* models produced a full verdict —
  13 NEW and 3 WORSENED threats that simply belong to the other system — while the sibling
  commands (`report --analysis-json`, `report --baseline`, `backlog --document`) already refuse
  exactly that pairing. `diff-analysis` is the one site of the four where a gate is armed.

Both guards are armed-only, like the engine-version one: with no gate flags the diff is still
informative, and "what does the finance pack add to this model?" is a legitimate question.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import Result
from otm_cli.cli import app
from otm_core_schema import load_document_from_yaml_path
from otm_industry_packs.loader import load_pack
from otm_threat_engine import analyze_document
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"
_SAAS = _ROOT / "examples" / "saas-ordering-v1.otm.yaml"

_GATE_TRIP = 3
_USAGE_ERROR = 1


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _out(result: Result) -> str:
    return (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")


def _store(analysis: object, target: Path) -> Path:
    target.write_text(json.dumps(analysis.model_dump(mode="json")), encoding="utf-8")  # type: ignore[attr-defined]
    return target


def _analysis_of(model: Path, target: Path, *, pack: str | None = None) -> Path:
    pack_def = load_pack(pack) if pack else None
    return _store(analyze_document(load_document_from_yaml_path(model), pack=pack_def), target)


# --- a pack change is not a model change ------------------------------------------------------


@pytest.fixture
def pack_mismatch(tmp_path: Path) -> tuple[Path, Path]:
    """The *same* model analysed twice: once plain, once with the finance pack."""
    plain = _analysis_of(_SAAS, tmp_path / "plain.json")
    packed = _analysis_of(_SAAS, tmp_path / "packed.json", pack="finance")
    return plain, packed


def test_an_armed_gate_refuses_to_judge_across_industry_packs(
    runner: CliRunner, pack_mismatch: tuple[Path, Path]
) -> None:
    plain, packed = pack_mismatch

    result = runner.invoke(app, ["diff-analysis", str(plain), str(packed), "--fail-on", "medium"])

    assert result.exit_code == _USAGE_ERROR


def test_the_pack_refusal_is_not_a_gate_trip(runner: CliRunner, pack_mismatch: tuple[Path, Path]) -> None:
    """Exit 3 would tell CI the model got worse; it did not change at all."""
    plain, packed = pack_mismatch

    result = runner.invoke(app, ["diff-analysis", str(plain), str(packed), "--fail-on", "medium"])

    assert result.exit_code != _GATE_TRIP


def test_the_pack_refusal_names_both_packs(runner: CliRunner, pack_mismatch: tuple[Path, Path]) -> None:
    plain, packed = pack_mismatch

    result = runner.invoke(app, ["diff-analysis", str(plain), str(packed), "--fail-on", "medium"])

    assert "finance" in _out(result)


def test_the_pack_refusal_says_which_side_had_no_pack(runner: CliRunner, pack_mismatch: tuple[Path, Path]) -> None:
    plain, packed = pack_mismatch

    result = runner.invoke(app, ["diff-analysis", str(plain), str(packed), "--fail-on", "medium"])

    assert "no pack" in _out(result)


def test_a_pack_mismatch_cannot_mask_a_real_regression(runner: CliRunner, pack_mismatch: tuple[Path, Path]) -> None:
    """The direction that used to report PASSED, exit 0, over a genuine risk increase."""
    plain, packed = pack_mismatch

    result = runner.invoke(app, ["diff-analysis", str(packed), str(plain), "--fail-on-risk-increase"])

    assert result.exit_code == _USAGE_ERROR


def test_without_a_gate_a_pack_mismatch_is_still_diffed(runner: CliRunner, pack_mismatch: tuple[Path, Path]) -> None:
    """Asking what the finance pack adds to a model is a legitimate, un-gated use of the diff."""
    plain, packed = pack_mismatch

    result = runner.invoke(app, ["diff-analysis", str(plain), str(packed)])

    assert result.exit_code == 0


def test_the_same_pack_on_both_sides_still_gates(runner: CliRunner, tmp_path: Path) -> None:
    """The guard must not disarm the gate for the setup CI actually uses."""
    baseline = _analysis_of(_SAAS, tmp_path / "b.json", pack="finance")
    revised = _analysis_of(_SAAS, tmp_path / "r.json", pack="finance")

    result = runner.invoke(app, ["diff-analysis", str(baseline), str(revised), "--fail-on", "low"])

    assert result.exit_code == 0


# --- two systems cannot produce one verdict ----------------------------------------------------


@pytest.fixture
def different_systems(tmp_path: Path) -> tuple[Path, Path]:
    return (
        _analysis_of(_MINIMAL, tmp_path / "minimal.json"),
        _analysis_of(_SAAS, tmp_path / "saas.json"),
    )


def test_an_armed_gate_refuses_two_different_systems(runner: CliRunner, different_systems: tuple[Path, Path]) -> None:
    minimal, saas = different_systems

    result = runner.invoke(app, ["diff-analysis", str(minimal), str(saas), "--fail-on", "high"])

    assert result.exit_code == _USAGE_ERROR


def test_the_two_systems_refusal_is_not_a_gate_trip(runner: CliRunner, different_systems: tuple[Path, Path]) -> None:
    """The old run exited 3, blaming a clean PR for the other system's 13 threats."""
    minimal, saas = different_systems

    result = runner.invoke(app, ["diff-analysis", str(minimal), str(saas), "--fail-on", "high"])

    assert result.exit_code != _GATE_TRIP


def test_the_two_systems_refusal_names_the_baseline_system(
    runner: CliRunner, different_systems: tuple[Path, Path]
) -> None:
    """Neither title appeared anywhere in the 53 lines the old verdict printed."""
    minimal, saas = different_systems

    result = runner.invoke(app, ["diff-analysis", str(minimal), str(saas), "--fail-on", "high"])

    assert load_document_from_yaml_path(_MINIMAL).metadata.title in _out(result)


def test_the_two_systems_refusal_names_the_revised_system(
    runner: CliRunner, different_systems: tuple[Path, Path]
) -> None:
    minimal, saas = different_systems

    result = runner.invoke(app, ["diff-analysis", str(minimal), str(saas), "--fail-on", "high"])

    assert load_document_from_yaml_path(_SAAS).metadata.title in _out(result)


def test_without_a_gate_two_systems_are_still_diffed(runner: CliRunner, different_systems: tuple[Path, Path]) -> None:
    minimal, saas = different_systems

    result = runner.invoke(app, ["diff-analysis", str(minimal), str(saas)])

    assert result.exit_code == 0
