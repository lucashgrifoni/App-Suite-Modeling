"""Coverage — CLI command display branches (init suggestion, root help)."""

from __future__ import annotations

from pathlib import Path

from otm_cli.cli import app
from typer.testing import CliRunner


def test_init_template_with_suggested_pack(tmp_path: Path) -> None:
    runner = CliRunner()
    out = tmp_path / "m.otm.yaml"
    # `api-backend` carries suggested_pack `cloud_native` -> the suggestion branch fires
    r = runner.invoke(app, ["init", str(out), "-t", "api-backend"])
    assert r.exit_code == 0
    assert "Suggestion" in r.output or "--pack" in r.output


def test_root_no_subcommand_prints_help() -> None:
    runner = CliRunner()
    r = runner.invoke(app, [])
    # root callback with no subcommand prints help text
    assert r.output


def test_explain_no_explanations_message(tmp_path: Path) -> None:
    import json

    runner = CliRunner()
    f = tmp_path / "an.json"
    f.write_text(json.dumps({"explanations": []}), encoding="utf-8")
    r = runner.invoke(app, ["explain", str(f), "--from", "analysis"])
    assert r.exit_code == 0
    assert "No explanations" in r.output  # empty -> "No explanations in this file." branch
