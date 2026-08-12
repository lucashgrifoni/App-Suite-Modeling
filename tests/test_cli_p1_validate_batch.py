"""Batch `otm validate` must diagnose as well as the single-file path.

`.pre-commit-hooks.yaml` runs `otm validate` with `pass_filenames: true`, so any commit that
touches two models takes the multi-file branch. That branch used to print only the file path,
throwing away the cause, the next step and the schema detail the single-file path prints —
leaving a contributor with a blocked commit and nothing to act on.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_cli.cli import app
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"

_BAD_KIND = (
    "model:\n"
    '  schema_version: "1.1.0"\n'
    "  system_type: web_application\n"
    "metadata:\n"
    '  title: "Bad kind"\n'
    "components:\n"
    "  - id: api\n"
    '    name: "API"\n'
    "    kind: not_a_real_kind\n"
    "data_flows: []\n"
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _wide_console(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "300")


def _out(result: object) -> str:
    return (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")


def test_batch_validate_keeps_the_schema_detail(runner: CliRunner, tmp_path: Path) -> None:
    bad = tmp_path / "bad.otm.yaml"
    bad.write_text(_BAD_KIND, encoding="utf-8")

    r = runner.invoke(app, ["validate", str(_MINIMAL), str(bad)])
    out = _out(r)
    assert r.exit_code == 1
    assert "Invalid" in out
    assert "components" in out, "the batch branch dropped the field path"
    assert "datastore" in out, "the batch branch dropped the expected-values list"
    assert "Next step" in out, "the batch branch dropped the actionable next step"


def test_batch_validate_still_reports_every_bad_file(runner: CliRunner, tmp_path: Path) -> None:
    """Adding the detail must not turn the batch branch back into fail-fast."""
    bad_a = tmp_path / "a.otm.yaml"
    bad_b = tmp_path / "b.otm.yaml"
    bad_a.write_text(_BAD_KIND, encoding="utf-8")
    bad_b.write_text(_BAD_KIND, encoding="utf-8")

    r = runner.invoke(app, ["validate", str(_MINIMAL), str(bad_a), str(bad_b)])
    out = _out(r)
    assert r.exit_code == 1
    assert "a.otm.yaml" in out
    assert "b.otm.yaml" in out
    assert out.count("Invalid") == 2
