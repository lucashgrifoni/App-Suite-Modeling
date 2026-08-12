"""Phase-2 regressions for `otm_cli.shared.emit`, the one module every `-o` flag goes through.

Two defects, both of them in how the destination file is opened:

* the write was guarded by `except PermissionError` alone, so every *other* `OSError` — a
  filename Windows rejects, a path component that is really a file, a path over MAX_PATH —
  escaped as a raw traceback carrying the maintainer's absolute source paths, contradicting the
  "user error, no stack trace" contract in `docs/features/CLI.md`;
* `Path.write_text` truncates the destination and then streams into it, so interrupting a run
  inside that window destroyed a good previous artifact and left a 0-byte file in its place.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import Result
from otm_cli.cli import app
from otm_cli.shared.emit import write_bytes_file, write_json_file, write_text_file
from otm_cli.shared.errors import CliUserError
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = str(_ROOT / "examples" / "minimal.otm.yaml")

_PRIOR = "PRIOR-GOOD-ARTIFACT"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _out(result: Result) -> str:
    return (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")


# --- every OSError, not just PermissionError -----------------------------------------------


def test_a_filename_the_os_rejects_is_a_clean_error(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["analyze", _MINIMAL, "-q", "--json-out", str(tmp_path / "out?.json")])

    assert result.exit_code == 1


def test_a_filename_the_os_rejects_does_not_escape_as_an_oserror(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["analyze", _MINIMAL, "-q", "--json-out", str(tmp_path / "out?.json")])

    assert not isinstance(result.exception, OSError)


def test_a_filename_the_os_rejects_names_the_destination(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["analyze", _MINIMAL, "-q", "--json-out", str(tmp_path / "out?.json")])

    assert "cannot write to" in _out(result)


def test_writing_through_an_existing_file_does_not_escape_as_an_oserror(runner: CliRunner, tmp_path: Path) -> None:
    """`-o model.otm.yaml/x.yaml` — the pre-check only asked whether the parent *existed*."""
    blocker = tmp_path / "blocker.yaml"
    blocker.write_text("not a directory", encoding="utf-8")

    result = runner.invoke(app, ["export", _MINIMAL, "-o", str(blocker / "x.yaml")])

    assert not isinstance(result.exception, OSError)


def test_writing_through_an_existing_file_says_so(runner: CliRunner, tmp_path: Path) -> None:
    blocker = tmp_path / "blocker2.yaml"
    blocker.write_text("not a directory", encoding="utf-8")

    result = runner.invoke(app, ["export", _MINIMAL, "-o", str(blocker / "x.yaml")])

    assert "not a directory" in _out(result)


def test_a_blank_output_name_does_not_escape_as_an_oserror(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["init", "   "])

    assert not isinstance(result.exception, OSError)


def test_the_pdf_writer_is_guarded_too(runner: CliRunner, tmp_path: Path) -> None:
    """`write_bytes_file` had the identical narrow `except`."""
    pytest.importorskip("xhtml2pdf")

    result = runner.invoke(app, ["report", _MINIMAL, "-l", "executive", "-f", "pdf", "-o", str(tmp_path / "r?.pdf")])

    assert not isinstance(result.exception, OSError)


def test_write_text_file_still_reports_permission_denied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The pre-existing PermissionError wording must survive the widened guard."""

    def _deny(self: Path, *args: object, **kwargs: object) -> int:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(Path, "write_text", _deny)

    with pytest.raises(CliUserError) as excinfo:
        write_text_file(content="x", output=tmp_path / "denied.txt")
    assert "permission denied" in excinfo.value.cause


def test_write_bytes_file_still_reports_permission_denied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _deny(self: Path, data: bytes) -> int:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(Path, "write_bytes", _deny)

    with pytest.raises(CliUserError) as excinfo:
        write_bytes_file(content=b"x", output=tmp_path / "denied.bin")
    assert "permission denied" in excinfo.value.cause


# --- atomic replacement ---------------------------------------------------------------------


def test_a_failed_write_leaves_the_previous_artifact_intact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`Path.write_text` truncated the destination first; the good prior artifact was gone."""
    target = tmp_path / "artifact.json"
    target.write_text(_PRIOR, encoding="utf-8")

    def _die(self: Path, *args: object, **kwargs: object) -> int:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(Path, "write_text", _die)
    with pytest.raises(CliUserError):
        write_text_file(content="new content", output=target)

    assert target.read_text(encoding="utf-8") == _PRIOR


def test_a_failed_binary_write_leaves_the_previous_artifact_intact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "artifact.pdf"
    target.write_bytes(_PRIOR.encode())

    def _die(self: Path, data: bytes) -> int:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(Path, "write_bytes", _die)
    with pytest.raises(CliUserError):
        write_bytes_file(content=b"new bytes", output=target)

    assert target.read_bytes() == _PRIOR.encode()


def test_a_failed_rename_leaves_no_partial_file_at_the_destination(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Interrupting between write and rename must never expose a 0-byte destination."""
    target = tmp_path / "never.json"

    def _die(src: object, dst: object) -> None:
        raise OSError(5, "Input/output error")

    monkeypatch.setattr(os, "replace", _die)
    with pytest.raises(CliUserError):
        write_text_file(content="new content", output=target)

    assert not target.exists()


def test_a_failed_write_leaves_no_temp_file_behind(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "tidy.json"

    def _die(src: object, dst: object) -> None:
        raise OSError(5, "Input/output error")

    monkeypatch.setattr(os, "replace", _die)
    with pytest.raises(CliUserError):
        write_text_file(content="new content", output=target)

    assert list(tmp_path.iterdir()) == []


def test_a_successful_write_replaces_the_previous_artifact(tmp_path: Path) -> None:
    target = tmp_path / "artifact.txt"
    target.write_text(_PRIOR, encoding="utf-8")

    write_text_file(content="fresh", output=target)

    assert target.read_text(encoding="utf-8") == "fresh"


def test_a_successful_write_leaves_only_the_artifact(tmp_path: Path) -> None:
    target = tmp_path / "solo.txt"

    write_text_file(content="fresh", output=target)

    assert [p.name for p in tmp_path.iterdir()] == ["solo.txt"]


def test_a_successful_binary_write_replaces_the_previous_artifact(tmp_path: Path) -> None:
    target = tmp_path / "artifact.bin"
    target.write_bytes(b"old")

    write_bytes_file(content=b"\x00\x01fresh", output=target)

    assert target.read_bytes() == b"\x00\x01fresh"


def test_json_writer_still_round_trips(tmp_path: Path) -> None:
    target = tmp_path / "payload.json"

    write_json_file(payload={"acentuação": 1}, output=target)

    assert '"acentuação": 1' in target.read_text(encoding="utf-8")


def test_a_relative_destination_in_the_current_directory_works(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`Path("x.json").parent` is `.`; the temp file has to land there, not in the cwd's parent."""
    monkeypatch.chdir(tmp_path)

    write_text_file(content="here", output=Path("bare.json"))

    assert (tmp_path / "bare.json").read_text(encoding="utf-8") == "here"
