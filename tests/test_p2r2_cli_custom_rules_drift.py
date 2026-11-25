"""Round-2 regression: organisation rules must reach the `otm diff` drift gate.

`docs/features/CUSTOM_RULES.md` states that "rules flow into everything downstream, including the
drift gate — so a pull request that introduces a component violating an organisation rule can fail
the build", and illustrates it with the composite action's YAML. The composite action gates via
`otm diff` (`action.yml`), and `otm diff` had no `--rules` option at all: the documented CI setup
loaded no rules, saw no custom threat and reported PASSED with exit 0. The doc's own fallback
(`otm analyze --rules` as a step) cannot gate either — `analyze` has no `--fail-on`.

Both sides of the comparison run under the one ruleset, exactly as `--pack` and `--methodology`
already do: a rule that fired on the baseline too is not a regression the PR introduced.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import Result
from otm_cli.cli import app
from typer.testing import CliRunner

_GATE_TRIP = 3

_BASE_MODEL = """\
model:
  schema_version: "1.1.0"
  system_type: web_application
  industry_sector: saas
metadata:
  title: "Drift demo"
trust_boundaries:
  - id: net
    name: "Rede"
    member_component_ids: [app]
components:
  - id: app
    name: "App"
    kind: process
    in_trust_boundary: net
data_flows: []
assets: []
threats: []
mitigations: []
evidence_suggestions: []
"""

_DEBUG_FLAG = "    supports_debug_features: true\n"

_ORG_RULES = """\
id: orgpolicy
rules:
  - id: no_debug_in_prod
    title: "Debug features enabled violates the production standard"
    stride: elevation_of_privilege
    match:
      component:
        supports_debug_features: true
    likelihood_delta: 2
    impact_delta: 2
"""

_CUSTOM_THREAT_ID = "custom_orgpolicy_no_debug_in_prod_app"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _out(result: Result) -> str:
    return (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")


@pytest.fixture
def org_rules(tmp_path: Path) -> Path:
    rules = tmp_path / "org-rules.yaml"
    rules.write_text(_ORG_RULES, encoding="utf-8")
    return rules


@pytest.fixture
def baseline_model(tmp_path: Path) -> Path:
    model = tmp_path / "base.otm.yaml"
    model.write_text(_BASE_MODEL, encoding="utf-8")
    return model


@pytest.fixture
def violating_model(tmp_path: Path) -> Path:
    """The same model with the one line that breaks the organisation rule."""
    model = tmp_path / "rev.otm.yaml"
    model.write_text(_BASE_MODEL.replace("    in_trust_boundary: net\n", "    in_trust_boundary: net\n" + _DEBUG_FLAG))
    return model


@pytest.fixture
def gated_drift(runner: CliRunner, baseline_model: Path, violating_model: Path, org_rules: Path) -> Result:
    """The documented CI line: the drift gate, with the organisation rules loaded."""
    return runner.invoke(
        app,
        [
            "diff",
            str(baseline_model),
            str(violating_model),
            "--with-analysis",
            "--rules",
            str(org_rules),
            "--fail-on",
            "high",
        ],
    )


def test_an_org_rule_violation_introduced_by_the_change_fails_the_build(gated_drift: Result) -> None:
    assert gated_drift.exit_code == _GATE_TRIP


def test_the_gate_names_the_custom_rule_that_tripped_it(gated_drift: Result) -> None:
    """A red build that does not say which rule broke sends the developer nowhere."""
    assert _CUSTOM_THREAT_ID in _out(gated_drift)


def test_the_same_rules_on_an_unchanged_model_stay_green(
    runner: CliRunner, violating_model: Path, org_rules: Path
) -> None:
    """The rule fires on BOTH sides, so it is pre-existing debt and not this PR's regression."""
    result = runner.invoke(
        app,
        [
            "diff",
            str(violating_model),
            str(violating_model),
            "--with-analysis",
            "--rules",
            str(org_rules),
            "--fail-on",
            "high",
        ],
    )

    assert result.exit_code == 0


def test_without_the_rules_file_the_same_drift_is_invisible_to_the_gate(
    runner: CliRunner, baseline_model: Path, violating_model: Path
) -> None:
    """Pins the opt-in boundary: the base engine has no opinion about `supports_debug_features`."""
    result = runner.invoke(
        app, ["diff", str(baseline_model), str(violating_model), "--with-analysis", "--fail-on", "high"]
    )

    assert result.exit_code == 0


def test_a_broken_rules_file_is_a_clean_usage_error(
    runner: CliRunner, baseline_model: Path, violating_model: Path, tmp_path: Path
) -> None:
    """`diff --rules` owes the same error contract as `analyze --rules`, not a traceback."""
    broken = tmp_path / "broken.yaml"
    broken.write_text("rules: [{}]\n", encoding="utf-8")

    result = runner.invoke(
        app, ["diff", str(baseline_model), str(violating_model), "--with-analysis", "--rules", str(broken)]
    )

    assert result.exit_code == 1
