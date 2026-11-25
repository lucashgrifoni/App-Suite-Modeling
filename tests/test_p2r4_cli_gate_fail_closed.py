"""Round-4 regression: an armed drift gate must never answer `0` without a verdict.

The reproduction, from the outside:

    otm diff base.otm.yaml revised.otm.yaml --fail-on high        -> FAILED, exit 3
    <add one line `methodology: linddun` to revised.otm.yaml>
    otm diff base.otm.yaml revised.otm.yaml --fail-on high        -> NOT EVALUATED, exit 0

One line inside the artifact under review turned a FAILED verdict into a green build, and
`--auto-methodology` did the same with no edit at all. `action.yml` maps exit 0 to a job that
passes, and the README's example wiring pins no methodology, so that was the default CI setup.

The two sibling "the delta is not attributable to the model change" conditions — engine-version
mismatch and pack mismatch — both fail CLOSED with exit 1 on `diff-analysis`. This one now does
too. `tripped` stays False (the policy was not violated; nothing was judged), so the fix is in
the exit-code mapping, which is where the CI contract lives.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_cli.cli import app
from otm_cli.shared.gate import gate_exit_code
from otm_threat_engine.gate import GatePolicy, GateResult
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_BASE = _ROOT / "examples" / "saas-ordering-v1.otm.yaml"

#: The insecure edit: the user->WAF flow loses TLS and authentication. A real regression that the
#: gate reports as one NEW critical threat plus one worsened threat crossing into critical.
_SECURE_FLOW = """  - id: user_to_waf
    from_component: user
    to_component: waf
    protocol: "HTTPS"
    authenticated: true
    encrypted: true"""
_INSECURE_FLOW = """  - id: user_to_waf
    from_component: user
    to_component: waf
    protocol: "HTTP"
    authenticated: false
    encrypted: false"""


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def pair(tmp_path: Path) -> tuple[Path, Path]:
    """(baseline, revised) — the revised model carries a genuine high-severity regression."""
    base_text = _BASE.read_text(encoding="utf-8")
    baseline = tmp_path / "base.otm.yaml"
    baseline.write_text(base_text, encoding="utf-8")
    revised_text = base_text.replace(_SECURE_FLOW, _INSECURE_FLOW)
    assert revised_text != base_text, "fixture drift: the baseline no longer contains the secure flow"
    revised = tmp_path / "revised.otm.yaml"
    revised.write_text(revised_text, encoding="utf-8")
    return baseline, revised


def _with_methodology(path: Path, methodology: str) -> Path:
    """The same model plus one line: `methodology: <x>` under `model:`."""
    out = path.with_name(f"{path.stem}-{methodology}.otm.yaml")
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    patched = []
    for line in lines:
        patched.append(line)
        if line.startswith("model:"):
            patched.append(f"  methodology: {methodology}\n")
    out.write_text("".join(patched), encoding="utf-8")
    return out


def _diff(runner: CliRunner, *args: str):
    return runner.invoke(app, ["diff", *args, "--fail-on", "high", "--summary-only"])


def test_the_regression_trips_the_gate_when_both_sides_share_a_lens(runner: CliRunner, pair: tuple[Path, Path]) -> None:
    """Control: without the methodology line the same pair is a red build, exit 3."""
    baseline, revised = pair

    result = _diff(runner, str(baseline), str(revised))

    assert result.exit_code == 3, result.output
    assert "FAILED" in result.output


def test_changing_the_methodology_inside_the_reviewed_model_cannot_green_the_build(
    runner: CliRunner, pair: tuple[Path, Path]
) -> None:
    """The bug: `methodology: linddun` in the revised file made the gate answer 0."""
    baseline, revised = pair
    revised_with_lens = _with_methodology(revised, "linddun")

    result = _diff(runner, str(baseline), str(revised_with_lens))

    assert result.exit_code != 0, result.output
    assert "NOT EVALUATED" in result.output
    assert "PASSED" not in result.output


def test_a_gate_that_could_not_judge_exits_one_like_its_sibling_conditions(
    runner: CliRunner, pair: tuple[Path, Path]
) -> None:
    """Exit 1, not 3: the policy was not violated, the command could not produce a verdict.

    That is the same code `diff-analysis` already returns for an engine-version or pack mismatch,
    so a CI script keeps one meaning per code.
    """
    baseline, revised = pair

    result = _diff(runner, str(baseline), str(_with_methodology(revised, "linddun")))

    assert result.exit_code == 1, result.output


def test_the_report_names_the_flag_that_restores_a_verdict(runner: CliRunner, pair: tuple[Path, Path]) -> None:
    """A refusal that does not say how to get past it just moves the failure to the operator."""
    baseline, revised = pair

    result = _diff(runner, str(baseline), str(_with_methodology(revised, "linddun")))

    assert "--methodology" in result.output


def test_pinning_the_lens_restores_the_verdict_on_the_same_pair(runner: CliRunner, pair: tuple[Path, Path]) -> None:
    """The documented way out must actually work, or the fix only breaks the gate differently."""
    baseline, revised = pair
    revised_with_lens = _with_methodology(revised, "linddun")

    result = _diff(runner, str(baseline), str(revised_with_lens), "-m", "stride")

    assert result.exit_code == 3, result.output
    assert "FAILED" in result.output


def test_auto_methodology_cannot_disable_the_gate_either(runner: CliRunner, pair: tuple[Path, Path]) -> None:
    """The second path to the same bypass: the recommendation differs between the two sides.

    `--auto-methodology` needs no edit to the file at all, so it has to fail closed as well.
    """
    baseline, revised = pair
    # A component whose technology names an LLM flips the automatic recommendation to plot4ai on
    # the revised side only, so the two analyses run under different lenses.
    revised_text = revised.read_text(encoding="utf-8")
    marker = "components:\n"
    assert marker in revised_text
    with_llm = revised_text.replace(
        marker,
        marker + '  - id: llm\n    name: "Assistente"\n    kind: process\n    technology: "LLM RAG"\n',
        1,
    )
    llm_model = revised.with_name("revised-llm.otm.yaml")
    llm_model.write_text(with_llm, encoding="utf-8")

    result = _diff(runner, str(baseline), str(llm_model), "--auto-methodology")

    assert result.exit_code != 0, result.output


def test_an_unarmed_diff_still_reports_a_methodology_switch_without_failing(
    runner: CliRunner, pair: tuple[Path, Path]
) -> None:
    """The opposite failure to guard against: no `--fail-on`, no gate, no refusal.

    Reading the diff between two models on different lenses is a legitimate question, and it was
    answerable before this change. It still is.
    """
    baseline, revised = pair

    result = runner.invoke(app, ["diff", str(baseline), str(_with_methodology(revised, "linddun")), "--summary-only"])

    assert result.exit_code == 0, result.output
    assert "NOT EVALUATED" not in result.output


def test_diff_analysis_maps_the_same_verdict_to_the_same_code(runner: CliRunner, tmp_path: Path) -> None:
    """`diff-analysis` arms the same policy, so it must answer CI identically."""
    baseline, revised = tmp_path / "a.json", tmp_path / "b.json"
    stride = runner.invoke(app, ["analyze", str(_BASE), "--json-out", str(baseline), "-q"])
    assert stride.exit_code == 0, stride.output
    linddun = runner.invoke(app, ["analyze", str(_BASE), "-m", "linddun", "--json-out", str(revised), "-q"])
    assert linddun.exit_code == 0, linddun.output

    result = runner.invoke(app, ["diff-analysis", str(baseline), str(revised), "--fail-on", "high"])

    assert result.exit_code == 1, result.output
    assert "NOT EVALUATED" in result.output


def test_gate_exit_code_maps_the_three_states() -> None:
    """The mapping itself, without a filesystem: pass 0, no verdict 1, tripped 3."""
    policy = GatePolicy(fail_on="high")

    assert gate_exit_code(GateResult(tripped=False, policy=policy)) == 0
    assert gate_exit_code(GateResult(tripped=False, policy=policy, not_evaluated_reason="methodology_changed")) == 1
    assert gate_exit_code(GateResult(tripped=True, policy=policy)) == 3
