"""Round-4 regression: an interrupted write must not leave its temp file behind.

`_write_atomically` fills a sibling `.otm<hex>.part` and renames it over the destination, and it
removed that temp only inside `except OSError`. Ctrl-C raises `KeyboardInterrupt`, which is a
`BaseException` and not an `OSError`, so it walked straight past the cleanup and left a hidden,
sometimes multi-megabyte `.part` file in the working directory that no later run ever swept — in
CI, exactly where an artifact-upload glob picks it up. The function's own docstring names "Ctrl-C,
a cancelled CI job" as the case it exists for.

The destination guarantee (old artifact or complete new one, never a truncated one) is asserted
alongside, because a cleanup that reached the destination would be a worse bug than the leak.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_cli.shared.emit import write_text_file


def _part_files(directory: Path) -> list[Path]:
    return sorted(directory.glob(".otm*.part"))


def test_keyboard_interrupt_during_the_write_leaves_no_temp_file(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    destination = tmp_path / "report.md"
    destination.write_text("previous artifact", encoding="utf-8")

    def _interrupt(self: Path, *args: object, **kwargs: object) -> int:
        raise KeyboardInterrupt

    monkeypatch.setattr(Path, "write_text", _interrupt)

    with pytest.raises(KeyboardInterrupt):
        write_text_file(content="new artifact", output=destination)

    assert _part_files(tmp_path) == [], "an interrupted write left its `.part` file behind"
    assert destination.read_text(encoding="utf-8") == "previous artifact"


def test_a_bare_base_exception_during_the_write_also_cleans_up(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    """Not only Ctrl-C: `SystemExit`, `MemoryError` and a timeout signal escape the same way."""
    destination = tmp_path / "report.md"

    def _abort(self: Path, *args: object, **kwargs: object) -> int:
        raise SystemExit(1)

    monkeypatch.setattr(Path, "write_text", _abort)

    with pytest.raises(SystemExit):
        write_text_file(content="new artifact", output=destination)

    assert _part_files(tmp_path) == []
    assert not destination.exists(), "an aborted first write must not create the destination"


def test_a_successful_write_leaves_no_temp_file(tmp_path: Path) -> None:
    destination = tmp_path / "report.md"
    write_text_file(content="artifact", output=destination)

    assert destination.read_text(encoding="utf-8") == "artifact"
    assert _part_files(tmp_path) == []


def test_a_cleanup_that_cannot_delete_does_not_replace_the_real_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The user must still see the interruption, not a traceback about a `.part` path."""
    destination = tmp_path / "report.md"

    def _interrupt(self: Path, *args: object, **kwargs: object) -> int:
        raise KeyboardInterrupt

    def _locked(self: Path, **kwargs: object) -> None:
        raise PermissionError("file is open in another process")

    monkeypatch.setattr(Path, "write_text", _interrupt)
    monkeypatch.setattr(Path, "unlink", _locked)

    with pytest.raises(KeyboardInterrupt):
        write_text_file(content="new artifact", output=destination)


def test_an_oserror_during_the_write_still_cleans_up_and_still_raises_a_cli_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The path that already worked must keep working, and keep its `CliUserError` wrapper."""
    from otm_cli.shared.errors import CliUserError

    destination = tmp_path / "report.md"

    def _fail(self: Path, *args: object, **kwargs: object) -> int:
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", _fail)

    with pytest.raises(CliUserError):
        write_text_file(content="new artifact", output=destination)

    assert _part_files(tmp_path) == []
