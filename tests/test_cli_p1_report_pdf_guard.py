"""`otm report -f pdf -o` must fail like every other writer, not with a raw traceback.

The Markdown branches of `report` route through `shared.emit.write_text_file`, which pre-checks
the parent directory and maps `PermissionError` onto a `CliUserError`. The PDF branch called
`Path.write_bytes` directly, so a missing `-o` parent dumped a Python stack trace into the CI
log — after the whole PDF had already been rendered and then discarded.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_cli.cli import app
from otm_cli.shared.emit import write_bytes_file
from otm_cli.shared.errors import CliUserError
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _wide_console(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "300")


def _out(result: object) -> str:
    return (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")


def test_pdf_output_to_missing_directory_is_a_clean_error(runner: CliRunner, tmp_path: Path) -> None:
    pytest.importorskip("xhtml2pdf")
    target = tmp_path / "nodir" / "r.pdf"
    r = runner.invoke(app, ["report", str(_MINIMAL), "--level", "executive", "-f", "pdf", "-o", str(target)])
    assert r.exit_code == 1
    assert not isinstance(r.exception, FileNotFoundError), "unhandled exception on a shipped output path"
    assert "parent directory does not exist" in _out(r)


def test_markdown_output_to_missing_directory_is_the_same_contract(runner: CliRunner, tmp_path: Path) -> None:
    """Control: the two branches must agree."""
    target = tmp_path / "nodir" / "r.md"
    r = runner.invoke(app, ["report", str(_MINIMAL), "--level", "executive", "-f", "markdown", "-o", str(target)])
    assert r.exit_code == 1
    assert "parent directory does not exist" in _out(r)


def test_write_bytes_file_rejects_a_missing_parent(tmp_path: Path) -> None:
    with pytest.raises(CliUserError) as excinfo:
        write_bytes_file(content=b"x", output=tmp_path / "nodir" / "x.bin")
    assert "parent directory does not exist" in excinfo.value.cause


def test_write_bytes_file_maps_permission_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(self: Path, data: bytes) -> int:
        raise PermissionError(13, "Permission denied")

    monkeypatch.setattr(Path, "write_bytes", _boom)
    with pytest.raises(CliUserError) as excinfo:
        write_bytes_file(content=b"x", output=tmp_path / "x.bin")
    assert "permission denied" in excinfo.value.cause


def test_write_bytes_file_writes_the_payload(tmp_path: Path) -> None:
    target = tmp_path / "ok.bin"
    write_bytes_file(content=b"\x00\x01payload", output=target)
    assert target.read_bytes() == b"\x00\x01payload"
