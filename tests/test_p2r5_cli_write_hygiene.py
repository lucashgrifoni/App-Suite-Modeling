"""Round-5: the atomic writer must not leak its temp name, nor leave its temp files behind.

Two reports about the same `.otm<hex>.part` sibling:

* **The name leaks.** When `os.replace` fails — a read-only destination, or one another process
  holds open — `_write_failure` interpolated the raw `OSError`, whose `filename`/`filename2` are
  the temp path and the destination: `permission denied: [WinError 5] Acesso negado:
  '.otm9fe6f00c.part' -> 'ro.json'`. The user goes looking for a file they never typed and which
  no longer exists. The sibling helper `_temp_creation_failure` states the rule in its own
  docstring — "never quote the internal `.part` name the user never typed" — and honours it.
* **The file is left behind.** A kill the process cannot observe (`SIGKILL`, `Stop-Process
  -Force`) orphans the temp, and nothing ever swept it: three subsequent successful commands
  writing into the same directory all left a planted 33 MB orphan untouched. A CI job killed by
  its timeout leaves it for the artifact-upload glob to collect.

The sweep is deliberately age-gated. A `.part` that appeared a moment ago is indistinguishable
from the live temp of a concurrent `otm`, and deleting that one would break a write that was
going to succeed — a worse defect than the one being fixed. That direction is tested too.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from otm_cli.shared.emit import (
    _STALE_TEMP_AGE_SECONDS,
    _TMP_PREFIX,
    _TMP_SUFFIX,
    write_bytes_file,
    write_text_file,
)
from otm_cli.shared.errors import CliUserError


def _plant_temp(directory: Path, name: str, *, age_seconds: float, size: int = 32) -> Path:
    path = directory / name
    path.write_bytes(b"x" * size)
    when = time.time() - age_seconds
    os.utime(path, (when, when))
    return path


def _temps(directory: Path) -> list[str]:
    names = (p.name for p in directory.iterdir())
    return sorted(n for n in names if n.startswith(_TMP_PREFIX) and n.endswith(_TMP_SUFFIX))


# --- the leak ------------------------------------------------------------------------------


def test_a_failed_replace_does_not_quote_the_temp_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The reported message, reproduced through the real code path."""
    target = tmp_path / "ro.json"
    target.write_text('{"previous":"artifact"}', encoding="utf-8")

    def _denied(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        raise PermissionError(13, "Acesso negado", str(src), 5, str(dst))

    monkeypatch.setattr(os, "replace", _denied)

    with pytest.raises(CliUserError) as excinfo:
        write_text_file(content="new", output=target)

    assert _TMP_SUFFIX not in excinfo.value.cause
    assert _TMP_PREFIX not in excinfo.value.cause


def test_the_error_still_names_the_destination_the_user_typed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Hiding the temp name must not cost the user the path they can act on."""
    target = tmp_path / "ro.json"
    target.write_text("previous", encoding="utf-8")
    monkeypatch.setattr(os, "replace", _raise_permission_denied)

    with pytest.raises(CliUserError) as excinfo:
        write_text_file(content="new", output=target)

    assert "ro.json" in excinfo.value.failed
    assert "permission denied" in excinfo.value.cause


def test_the_error_keeps_the_operating_system_code(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The diagnostic a support thread needs survives; only the paths go."""
    monkeypatch.setattr(os, "replace", _raise_permission_denied)

    with pytest.raises(CliUserError) as excinfo:
        write_text_file(content="new", output=tmp_path / "x.json")

    assert "Acesso negado" in excinfo.value.cause
    assert "WinError 5" in excinfo.value.cause or "errno 13" in excinfo.value.cause


def test_a_non_permission_failure_is_scrubbed_the_same_way(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`the destination is not writable: …` took the same raw string."""

    def _invalid(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        raise OSError(22, "Invalid argument", str(src), 123, str(dst))

    monkeypatch.setattr(os, "replace", _invalid)

    with pytest.raises(CliUserError) as excinfo:
        write_text_file(content="new", output=tmp_path / "x.json")

    assert _TMP_SUFFIX not in excinfo.value.cause
    assert "Invalid argument" in excinfo.value.cause


def test_an_oserror_without_a_strerror_still_produces_a_cause(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _bare(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        raise OSError("something went wrong")

    monkeypatch.setattr(os, "replace", _bare)

    with pytest.raises(CliUserError) as excinfo:
        write_text_file(content="new", output=tmp_path / "x.json")

    assert "something went wrong" in excinfo.value.cause


def _raise_permission_denied(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
    raise PermissionError(13, "Acesso negado", str(src), 5, str(dst))


# --- the orphan ----------------------------------------------------------------------------


def test_a_stale_orphan_is_reclaimed_by_the_next_write(tmp_path: Path) -> None:
    orphan = _plant_temp(tmp_path, ".otmdeadbeef.part", age_seconds=_STALE_TEMP_AGE_SECONDS + 60, size=4096)

    write_text_file(content="artifact", output=tmp_path / "out.json")

    assert not orphan.exists()
    assert (tmp_path / "out.json").read_text(encoding="utf-8") == "artifact"


def test_the_binary_writer_sweeps_too(tmp_path: Path) -> None:
    orphan = _plant_temp(tmp_path, ".otm0123abcd.part", age_seconds=_STALE_TEMP_AGE_SECONDS + 60)

    write_bytes_file(content=b"pdf", output=tmp_path / "out.pdf")

    assert not orphan.exists()


def test_a_fresh_sibling_is_left_alone(tmp_path: Path) -> None:
    """The opposite defect: a concurrent `otm` writing here must not lose its temp file."""
    live = _plant_temp(tmp_path, ".otmfeedface.part", age_seconds=1.0)

    write_text_file(content="artifact", output=tmp_path / "out.json")

    assert live.exists()


@pytest.mark.parametrize(
    "name",
    [
        "report.part",  # a user's own file that ends the same way
        ".otm.part",  # right affixes, no random middle
        ".otmZZZZZZZZ.part",  # right length, not hex
        ".otmdeadbeef.parts",  # right prefix, wrong suffix
        ".otmdeadbeefcafe.part",  # right shape, wrong length
    ],
)
def test_a_file_that_only_looks_like_a_temp_is_left_alone(tmp_path: Path, name: str) -> None:
    """The sweep matches the exact name this writer generates and nothing else."""
    bystander = _plant_temp(tmp_path, name, age_seconds=_STALE_TEMP_AGE_SECONDS + 60)

    write_text_file(content="artifact", output=tmp_path / "out.json")

    assert bystander.exists()


def test_a_stale_directory_named_like_a_temp_is_left_alone(tmp_path: Path) -> None:
    directory = tmp_path / ".otmdeadbeef.part"
    directory.mkdir()
    old = time.time() - _STALE_TEMP_AGE_SECONDS - 60
    os.utime(directory, (old, old))

    write_text_file(content="artifact", output=tmp_path / "out.json")

    assert directory.is_dir()


def test_the_write_survives_an_orphan_that_cannot_be_removed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Hygiene must never become the error the user sees for a write that is otherwise fine."""
    _plant_temp(tmp_path, ".otmdeadbeef.part", age_seconds=_STALE_TEMP_AGE_SECONDS + 60)
    real_unlink = Path.unlink

    def _locked(self: Path, missing_ok: bool = False) -> None:
        if self.name == ".otmdeadbeef.part":
            raise PermissionError(13, "held open by another process")
        real_unlink(self, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", _locked)

    write_text_file(content="artifact", output=tmp_path / "out.json")

    assert (tmp_path / "out.json").read_text(encoding="utf-8") == "artifact"


def test_an_unlistable_directory_does_not_break_the_write(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _denied(path: object) -> object:
        raise PermissionError(13, "listing denied")

    monkeypatch.setattr(os, "scandir", _denied)

    write_text_file(content="artifact", output=tmp_path / "out.json")

    assert (tmp_path / "out.json").read_text(encoding="utf-8") == "artifact"


def test_an_orphan_that_vanishes_mid_sweep_does_not_break_the_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two `otm` runs sweeping the same directory: the loser must not raise on the winner's work."""

    class _Vanished:
        name = ".otmdeadbeef.part"
        path = str(tmp_path / ".otmdeadbeef.part")

        def is_file(self) -> bool:
            return True

        def stat(self) -> object:
            raise FileNotFoundError(2, "No such file or directory")

    class _Listing:
        def __enter__(self) -> list[object]:
            return [_Vanished()]

        def __exit__(self, *_exc: object) -> None:
            return None

    monkeypatch.setattr(os, "scandir", lambda _path: _Listing())

    write_text_file(content="artifact", output=tmp_path / "out.json")

    assert (tmp_path / "out.json").read_text(encoding="utf-8") == "artifact"


def test_a_successful_write_leaves_no_temp_of_its_own(tmp_path: Path) -> None:
    """Control: the writer under test is not itself the source of orphans."""
    write_text_file(content="artifact", output=tmp_path / "out.json")

    assert _temps(tmp_path) == []
