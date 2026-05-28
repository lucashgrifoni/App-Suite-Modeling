"""Regression — graceful errors on missing output directories and CLI flag conflicts.

Locks down B1, B2 and B3 from the v7.5.0 extreme-end-user validation.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_cli.cli import app
from otm_cli.shared.emit import write_json_file, write_text_file
from otm_cli.shared.errors import CliUserError
from typer.testing import CliRunner


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


def test_write_text_file_raises_cli_user_error_when_parent_missing(tmp_path: Path) -> None:
    target = tmp_path / "missing" / "out.txt"
    with pytest.raises(CliUserError) as exc:
        write_text_file(content="x", output=target)
    assert "parent directory does not exist" in exc.value.cause


def test_write_json_file_raises_cli_user_error_when_parent_missing(tmp_path: Path) -> None:
    target = tmp_path / "missing" / "out.json"
    with pytest.raises(CliUserError) as exc:
        write_json_file(payload={"a": 1}, output=target)
    assert "parent directory does not exist" in exc.value.cause


def test_init_in_missing_directory_exits_with_friendly_error(
    runner: CliRunner, tmp_path: Path
) -> None:
    target = tmp_path / "no_such_dir" / "model.otm.yaml"
    result = runner.invoke(app, ["init", str(target)])
    assert result.exit_code != 0
    combined = (result.stdout or "") + (result.stderr or "")
    assert "Traceback" not in combined
    assert "parent directory does not exist" in combined
    assert not target.exists()


def test_analyze_with_json_out_in_missing_directory_exits_cleanly(
    runner: CliRunner, tmp_path: Path
) -> None:
    model = tmp_path / "model.otm.yaml"
    runner.invoke(app, ["init", str(model)])
    target = tmp_path / "no_such_dir" / "out.json"
    result = runner.invoke(app, ["analyze", str(model), "-q", "--json-out", str(target)])
    assert result.exit_code != 0
    combined = (result.stdout or "") + (result.stderr or "")
    assert "Traceback" not in combined
    assert not target.exists()


@pytest.mark.parametrize(
    "subcmd,arg_for_output",
    [
        ("validate", None),  # no -o; expected to succeed
    ],
)
def test_validate_still_works_after_emit_change(
    runner: CliRunner, tmp_path: Path, subcmd: str, arg_for_output: str | None
) -> None:
    model = tmp_path / "model.otm.yaml"
    runner.invoke(app, ["init", str(model)])
    result = runner.invoke(app, [subcmd, str(model)])
    assert result.exit_code == 0


def test_analyze_methodology_and_auto_methodology_are_mutually_exclusive(
    runner: CliRunner, tmp_path: Path
) -> None:
    model = tmp_path / "model.otm.yaml"
    runner.invoke(app, ["init", str(model)])
    result = runner.invoke(
        app, ["analyze", str(model), "-m", "stride", "--auto-methodology"]
    )
    assert result.exit_code != 0
    combined = (result.stdout or "") + (result.stderr or "")
    assert "mutually exclusive" in combined


def test_init_template_in_missing_directory_exits_with_friendly_error(
    runner: CliRunner, tmp_path: Path
) -> None:
    target = tmp_path / "absent" / "from_template.otm.yaml"
    result = runner.invoke(app, ["init", str(target), "-t", "saas-web"])
    assert result.exit_code != 0
    combined = (result.stdout or "") + (result.stderr or "")
    assert "Traceback" not in combined
    assert "parent directory does not exist" in combined
