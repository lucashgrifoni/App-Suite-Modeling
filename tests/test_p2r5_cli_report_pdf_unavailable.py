"""Round-5: a PDF engine that cannot load must produce the designed error, not a traceback.

`pip install "open-threat-model[report]"` pulls `xhtml2pdf -> svglib -> rlPyCairo -> cairocffi`,
and `cairocffi` needs a native Cairo library that Windows does not ship. When it is absent the
import raises **OSError**, not ImportError — so it escaped the `except ImportError` guard in
`pdf_export.html_to_pdf_bytes` and the one in `report_service.run_report`, and the documented
command `otm report model.otm.yaml --level executive --format pdf` (docs/features/
PREMIUM_REPORTS.md) dumped a full Rich traceback ending in
`OSError: no library called "cairo-2" was found`, wrote nothing, and exited 1.

docs/features/CLI.md promises user errors "sem stack trace" in the three-line `Failure: / Likely
cause: / Next step:` shape, and the handler in `report_service` shows that shape was intended
here. The remedy differs from the package-missing one — telling someone whose extra is already
installed to install the extra is not a next step — so the reason now travels on the exception.
"""

from __future__ import annotations

import builtins
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest
from otm_cli.cli import app
from otm_report_premium import PdfSupportUnavailable, html_to_pdf_bytes
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"

#: What `cairocffi.dlopen` actually raises, first line verbatim from the reproduction.
_CAIRO_OSERROR = OSError(
    'no library called "cairo-2" was found\n'
    "cannot load library 'libcairo-2.dll': error 0x7e.  Additionally, "
    "ctypes.util.find_library() did not manage to locate a library called 'libcairo-2.dll'"
)


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _wide_console(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "300")


def _break_the_import(monkeypatch: pytest.MonkeyPatch, error: BaseException) -> None:
    """Make `from xhtml2pdf import pisa` fail the way a broken install fails."""
    real_import: Callable[..., Any] = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "xhtml2pdf":
            raise error
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)


def _out(result: object) -> str:
    return (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")


def test_a_missing_native_library_raises_the_optional_dependency_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """The root cause, at the layer that owns it."""
    _break_the_import(monkeypatch, _CAIRO_OSERROR)

    with pytest.raises(PdfSupportUnavailable) as excinfo:
        html_to_pdf_bytes("<html><body>x</body></html>")

    assert "Cairo" in excinfo.value.cause
    assert 'no library called "cairo-2" was found' in excinfo.value.cause


def test_a_missing_package_still_raises_its_own_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """The other branch must keep its own, different, remedy."""
    _break_the_import(monkeypatch, ImportError("No module named 'xhtml2pdf'"))

    with pytest.raises(PdfSupportUnavailable) as excinfo:
        html_to_pdf_bytes("<html><body>x</body></html>")

    assert "not installed" in excinfo.value.cause
    assert "open-threat-model[report]" in excinfo.value.next_step


@pytest.mark.parametrize("error", [_CAIRO_OSERROR, ImportError("No module named 'xhtml2pdf'")], ids=["cairo", "absent"])
def test_it_stays_an_import_error_so_existing_handlers_keep_working(
    monkeypatch: pytest.MonkeyPatch, error: BaseException
) -> None:
    """The CLI's `except` and the API's 501 both key on ImportError; neither may start missing."""
    _break_the_import(monkeypatch, error)

    with pytest.raises(ImportError):
        html_to_pdf_bytes("<html><body>x</body></html>")


@pytest.mark.parametrize("level", ["executive", "standard", "deep"])
def test_the_documented_command_reports_cleanly_instead_of_crashing(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, level: str
) -> None:
    _break_the_import(monkeypatch, _CAIRO_OSERROR)
    target = tmp_path / "relatorio.pdf"

    result = runner.invoke(app, ["report", str(_MINIMAL), "--level", level, "--format", "pdf", "-o", str(target)])

    assert result.exit_code == 1
    assert result.exception is None or isinstance(result.exception, SystemExit), _out(result)
    assert "Traceback" not in _out(result)
    assert not target.exists()


def test_the_message_keeps_the_three_line_shape(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _break_the_import(monkeypatch, _CAIRO_OSERROR)

    result = runner.invoke(
        app, ["report", str(_MINIMAL), "--level", "executive", "--format", "pdf", "-o", str(tmp_path / "r.pdf")]
    )

    out = _out(result)
    assert "Failure:" in out
    assert "Likely cause:" in out
    assert "Next step:" in out


def test_the_next_step_does_not_tell_a_satisfied_install_to_install_the_extra(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The half that made the old message useless in the environment that actually hits this."""
    _break_the_import(monkeypatch, _CAIRO_OSERROR)

    result = runner.invoke(
        app, ["report", str(_MINIMAL), "--level", "executive", "--format", "pdf", "-o", str(tmp_path / "r.pdf")]
    )

    out = _out(result)
    assert "open-threat-model[report]" not in out
    assert "Cairo" in out
    assert "--format markdown" in out


def test_the_markdown_format_is_unaffected_by_a_broken_pdf_stack(
    runner: CliRunner, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The escape hatch the message points at has to actually work."""
    _break_the_import(monkeypatch, _CAIRO_OSERROR)
    target = tmp_path / "r.md"

    result = runner.invoke(
        app, ["report", str(_MINIMAL), "--level", "executive", "--format", "markdown", "-o", str(target)]
    )

    assert result.exit_code == 0, _out(result)
    assert target.read_text(encoding="utf-8").startswith("# ")


def test_a_working_pdf_stack_still_produces_a_pdf(runner: CliRunner, tmp_path: Path) -> None:
    """The other direction: the guard must not refuse an install that is fine."""
    pytest.importorskip("xhtml2pdf")
    target = tmp_path / "ok.pdf"

    result = runner.invoke(app, ["report", str(_MINIMAL), "--level", "executive", "--format", "pdf", "-o", str(target)])

    assert result.exit_code == 0, _out(result)
    assert target.read_bytes().startswith(b"%PDF")
