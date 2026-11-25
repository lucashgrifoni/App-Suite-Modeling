"""Round-2 regressions for `otm_cli.shared.emit`, the module every `-o` flag goes through.

Three defects, all of them in what happens *around* the bytes:

* **The writer hung forever on a directory it could not create files in.** `tempfile.mkstemp`
  was doing the atomic write's temp-file creation, and on Windows CPython's `_mkstemp_inner`
  treats every `PermissionError` as a name collision while `os.access(dir, os.W_OK)` says the
  directory is writable — and Windows' `os.access` only inspects the read-only attribute, so it
  says `True` for a directory whose ACL denies file creation. The loop then retried up to
  `tempfile.TMP_MAX` (2_147_483_647) times: `otm export -o "C:/Program Files/x.yaml"` printed not
  one byte on stdout or stderr and never exited, measured still running at 540 s. In CI that
  blocks the step until the job timeout instead of failing in a second.

* **Naming an existing *directory* as the destination was diagnosed as "permission denied"**,
  telling the user to check permissions and close processes when neither had anything to do with
  it, and quoting an internal `.otmXXXXXXXX.part` path they never typed and cannot find.

* **Pointing the output at the input destroyed the input.** `otm analyze m.otm.yaml --json-out
  m.otm.yaml` (and `export -o`, `report -o`, `diagram -o`, `--sarif-out`) replaced the
  hand-authored, git-versioned model with the generated artifact, printed a success message and
  exited 0. `otm init` already refuses this class of overwrite, so the convention existed.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import Result
from otm_cli.cli import app
from otm_cli.shared.emit import _TMP_ATTEMPTS, write_text_file
from otm_cli.shared.errors import CliUserError
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"

#: Well above `_TMP_ATTEMPTS` and far below `tempfile.TMP_MAX`: enough head-room that a bounded
#: writer never reaches it, low enough that an unbounded one is caught in milliseconds instead of
#: hanging the test session the way it hung the CLI.
_RETRY_CEILING = 64


class _RetryStorm(RuntimeError):
    """Raised by the stub once the writer has clearly stopped bounding its retries."""


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _out(result: Result) -> str:
    return (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")


def _model_copy(tmp_path: Path, name: str = "model.otm.yaml") -> Path:
    target = tmp_path / name
    target.write_text(_MINIMAL.read_text(encoding="utf-8"), encoding="utf-8")
    return target


# --- the retry storm ------------------------------------------------------------------------


def _refusing_open(attempts: list[str], error: OSError):
    """Stand in for a directory whose ACL denies creation, counting how often we are asked."""

    def _refuse(path: object, flags: int, mode: int = 0o777) -> int:
        attempts.append(str(path))
        if len(attempts) > _RETRY_CEILING:
            raise _RetryStorm(f"the writer retried {len(attempts)} times without giving up")
        raise error

    return _refuse


@pytest.fixture
def denied_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[CliUserError, list[str]]:
    """One write into a directory that refuses every create; returns the error and the attempts.

    If the writer ever goes back to an unbounded loop, `_RetryStorm` escapes here and every test
    below reports an error rather than hanging — which is the regression signal.
    """
    attempts: list[str] = []
    monkeypatch.setattr(os, "open", _refusing_open(attempts, PermissionError(13, "Permission denied")))

    with pytest.raises(CliUserError) as excinfo:
        write_text_file(content="payload", output=tmp_path / "artifact.json")
    return excinfo.value, attempts


def test_a_directory_that_denies_creation_gives_up_after_a_bounded_number_of_attempts(
    denied_directory: tuple[CliUserError, list[str]],
) -> None:
    _error, attempts = denied_directory

    assert len(attempts) <= _TMP_ATTEMPTS


def test_a_directory_that_denies_creation_is_a_user_error_not_a_crash(
    denied_directory: tuple[CliUserError, list[str]],
) -> None:
    error, _attempts = denied_directory

    assert error.exit_code == 1


def test_a_directory_that_denies_creation_blames_the_directory(
    denied_directory: tuple[CliUserError, list[str]],
) -> None:
    error, _attempts = denied_directory

    assert "does not allow creating files" in error.cause


def test_a_directory_that_denies_creation_does_not_quote_the_internal_temp_name(
    denied_directory: tuple[CliUserError, list[str]],
) -> None:
    """The old message showed a random `.otmXXXXXXXX.part` path the user never typed."""
    error, _attempts = denied_directory

    assert ".part" not in error.cause


@pytest.fixture
def colliding_names(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[CliUserError, list[str]]:
    """Genuine name collisions: those *are* worth another draw, but still a bounded number."""
    attempts: list[str] = []
    monkeypatch.setattr(os, "open", _refusing_open(attempts, FileExistsError(17, "File exists")))

    with pytest.raises(CliUserError) as excinfo:
        write_text_file(content="payload", output=tmp_path / "artifact.json")
    return excinfo.value, attempts


def test_repeated_name_collisions_are_retried(colliding_names: tuple[CliUserError, list[str]]) -> None:
    _error, attempts = colliding_names

    assert len(attempts) == _TMP_ATTEMPTS


def test_repeated_name_collisions_end_in_a_user_error(colliding_names: tuple[CliUserError, list[str]]) -> None:
    error, _attempts = colliding_names

    assert error.exit_code == 1


def test_each_attempt_draws_a_different_temp_name(colliding_names: tuple[CliUserError, list[str]]) -> None:
    """Redrawing the same name would make the retry pointless."""
    _error, attempts = colliding_names

    assert len(set(attempts)) == len(attempts)


# --- the destination is a directory -----------------------------------------------------------


@pytest.fixture
def export_onto_a_directory(runner: CliRunner, tmp_path: Path) -> Result:
    destination = tmp_path / "reports"
    destination.mkdir()
    return runner.invoke(app, ["export", str(_MINIMAL), "-o", str(destination)])


def test_a_directory_destination_fails_cleanly(export_onto_a_directory: Result) -> None:
    assert export_onto_a_directory.exit_code == 1


def test_a_directory_destination_names_the_real_cause(export_onto_a_directory: Result) -> None:
    assert "existing directory" in _out(export_onto_a_directory)


def test_a_directory_destination_is_not_reported_as_permission_denied(export_onto_a_directory: Result) -> None:
    """The old wording sent the user after file permissions and a process holding a lock."""
    assert "permission denied" not in _out(export_onto_a_directory)


def test_init_onto_a_directory_does_not_claim_a_file_already_exists(runner: CliRunner, tmp_path: Path) -> None:
    """`--force` cannot help here, so offering it was the wrong next step."""
    destination = tmp_path / "somewhere"
    destination.mkdir()

    result = runner.invoke(app, ["init", str(destination)])

    assert "existing directory" in _out(result)


# --- the output path is the input path ---------------------------------------------------------


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["analyze", "{model}", "-q", "--json-out", "{model}"], id="analyze --json-out"),
        pytest.param(["analyze", "{model}", "-q", "--sarif-out", "{model}"], id="analyze --sarif-out"),
        pytest.param(["export", "{model}", "-f", "json", "-o", "{model}"], id="export -o"),
        pytest.param(["report", "{model}", "-o", "{model}"], id="report -o"),
        pytest.param(["diagram", "{model}", "-o", "{model}"], id="diagram -o"),
        pytest.param(["backlog", "{model}", "-o", "{model}"], id="backlog -o"),
        pytest.param(["precheck", "{model}", "--json-out", "{model}"], id="precheck --json-out"),
    ],
)
def test_writing_the_artifact_over_the_model_leaves_the_model_untouched(
    runner: CliRunner, tmp_path: Path, argv: list[str]
) -> None:
    model = _model_copy(tmp_path)
    before = model.read_bytes()

    runner.invoke(app, [arg.format(model=str(model)) for arg in argv])

    assert model.read_bytes() == before


def test_writing_the_artifact_over_the_model_is_a_usage_error(runner: CliRunner, tmp_path: Path) -> None:
    model = _model_copy(tmp_path)

    result = runner.invoke(app, ["export", str(model), "-o", str(model)])

    assert result.exit_code == 1


def test_writing_the_artifact_over_the_model_says_it_is_refusing(runner: CliRunner, tmp_path: Path) -> None:
    model = _model_copy(tmp_path)

    result = runner.invoke(app, ["export", str(model), "-o", str(model)])

    assert "refusing to overwrite the input file" in _out(result)


def test_the_same_file_reached_by_a_different_spelling_is_still_refused(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`./m.otm.yaml` and `m.otm.yaml` are one file; string comparison would have missed it."""
    _model_copy(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["export", "model.otm.yaml", "-o", os.path.join(".", "model.otm.yaml")])

    assert result.exit_code == 1


def test_a_secondary_input_is_protected_too(runner: CliRunner, tmp_path: Path) -> None:
    """`backlog analysis.json -d model.otm.yaml -o model.otm.yaml` destroyed the model as well."""
    model = _model_copy(tmp_path)
    analysis = tmp_path / "analysis.json"
    runner.invoke(app, ["analyze", str(model), "-q", "--json-out", str(analysis)])
    before = model.read_bytes()

    runner.invoke(app, ["backlog", str(analysis), "-d", str(model), "-o", str(model)])

    assert model.read_bytes() == before


def test_a_different_output_path_still_writes(runner: CliRunner, tmp_path: Path) -> None:
    """The guard must not cost the normal case: a distinct destination is written as before."""
    model = _model_copy(tmp_path)
    target = tmp_path / "exported.json"

    runner.invoke(app, ["export", str(model), "-f", "json", "-o", str(target)])

    assert target.is_file()
