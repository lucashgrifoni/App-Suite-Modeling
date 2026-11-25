"""Phase-2 regression: the documented template quick-start must actually run.

`docs/features/TEMPLATES_AND_PACKS.md` told new users to write `otm init -t saas-web -o
modelo.otm.yaml`. `otm init` takes the output path positionally and has no `-o`, so the block
died at its second command with "No such option: -o" and left the directory empty — every later
step then failed on a missing file. The sibling page `TEMPLATE_CATALOG.md` had the correct form
all along, so the two docs disagreed.

The test executes the block rather than pattern-matching it, so any future flag drift in these
commands fails here instead of on a first-time user's terminal.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_cli.cli import app
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_PAGE = _ROOT / "docs" / "features" / "TEMPLATES_AND_PACKS.md"
_HEADING = "## Fluxo rápido"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _quickstart_argv() -> list[list[str]]:
    """The `otm ...` lines of the first fenced block under the quick-start heading."""
    body = _PAGE.read_text(encoding="utf-8").split(_HEADING, 1)[1]
    block = body.split("```bash", 1)[1].split("```", 1)[0]
    return [line.split()[1:] for line in block.strip().splitlines() if line.strip().startswith("otm ")]


def test_quickstart_block_is_not_empty() -> None:
    assert _quickstart_argv()


def test_quickstart_block_still_starts_from_init() -> None:
    """Guards the parser above: a renamed heading or fence would silently test nothing."""
    commands = [argv[0] for argv in _quickstart_argv()]

    assert "init" in commands


def test_documented_quickstart_runs_end_to_end(
    runner: CliRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    for argv in _quickstart_argv():
        result = runner.invoke(app, argv)
        assert result.exit_code == 0, f"documented command failed: otm {' '.join(argv)}"


def test_documented_quickstart_creates_the_model_it_then_uses(
    runner: CliRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    for argv in _quickstart_argv():
        runner.invoke(app, argv)

    assert (tmp_path / "modelo.otm.yaml").is_file()
