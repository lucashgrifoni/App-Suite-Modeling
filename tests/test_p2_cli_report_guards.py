"""Phase-2 regressions for `otm report` flag handling.

Three defects, all of them "the command accepted the request and quietly produced something
else":

* `--analysis-json` / `--baseline` paired a model with an unrelated system's analysis and
  emitted one authoritative-looking artifact carrying two identities;
* `-f pdf` without `--level` wrote Markdown bytes into the `.pdf` path the user named and
  exited 0;
* `--locale` was hard-coded away on the PDF branch, so every premium PDF was English even
  when pt-BR (the documented default) was requested.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_cli.cli import app
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = str(_ROOT / "examples" / "minimal.otm.yaml")
_SAAS = str(_ROOT / "examples" / "saas-ordering-v1.otm.yaml")


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _analysis_of(runner: CliRunner, tmp_path: Path, model: str, name: str) -> Path:
    out = tmp_path / name
    result = runner.invoke(app, ["analyze", model, "--json-out", str(out), "--quiet"])
    assert result.exit_code == 0
    return out


def _text(result: object) -> str:
    stdout = getattr(result, "stdout", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    return stdout + stderr


# --- mismatched analysis -------------------------------------------------------------------


def test_report_refuses_an_analysis_json_describing_another_system(runner: CliRunner, tmp_path: Path) -> None:
    """The report used to be titled after the model and filled with the other model's threats."""
    foreign = _analysis_of(runner, tmp_path, _MINIMAL, "foreign.json")
    out = tmp_path / "mismatch.md"

    result = runner.invoke(
        app, ["report", _SAAS, "--level", "standard", "--analysis-json", str(foreign), "-o", str(out)]
    )

    assert result.exit_code == 1


def test_report_mismatch_error_names_both_systems(runner: CliRunner, tmp_path: Path) -> None:
    foreign = _analysis_of(runner, tmp_path, _MINIMAL, "foreign2.json")

    result = runner.invoke(app, ["report", _SAAS, "--level", "standard", "--analysis-json", str(foreign)])

    assert "--analysis-json" in _text(result)


def test_report_mismatch_writes_no_artifact(runner: CliRunner, tmp_path: Path) -> None:
    foreign = _analysis_of(runner, tmp_path, _MINIMAL, "foreign3.json")
    out = tmp_path / "never.md"

    runner.invoke(app, ["report", _SAAS, "--level", "standard", "--analysis-json", str(foreign), "-o", str(out)])

    assert not out.exists()


def test_report_refuses_a_baseline_describing_another_system(runner: CliRunner, tmp_path: Path) -> None:
    """`--baseline` presented two unrelated models as one system regressing between revisions."""
    foreign = _analysis_of(runner, tmp_path, _MINIMAL, "foreign4.json")

    result = runner.invoke(app, ["report", _SAAS, "--level", "deep", "--baseline", str(foreign)])

    assert result.exit_code == 1


def test_report_baseline_mismatch_error_names_the_flag(runner: CliRunner, tmp_path: Path) -> None:
    foreign = _analysis_of(runner, tmp_path, _MINIMAL, "foreign5.json")

    result = runner.invoke(app, ["report", _SAAS, "--level", "deep", "--baseline", str(foreign)])

    assert "--baseline" in _text(result)


def test_report_legacy_level_also_refuses_a_foreign_analysis(runner: CliRunner, tmp_path: Path) -> None:
    """The legacy (no `--level`) branch honours `--analysis-json`, so it needs the same guard."""
    foreign = _analysis_of(runner, tmp_path, _MINIMAL, "foreign6.json")

    result = runner.invoke(app, ["report", _SAAS, "--analysis-json", str(foreign)])

    assert result.exit_code == 1


def test_report_accepts_the_matching_analysis_json(runner: CliRunner, tmp_path: Path) -> None:
    """The guard must not get in the way of the documented happy path."""
    own = _analysis_of(runner, tmp_path, _SAAS, "own.json")
    out = tmp_path / "ok.md"

    result = runner.invoke(app, ["report", _SAAS, "--level", "standard", "--analysis-json", str(own), "-o", str(out)])

    assert result.exit_code == 0


def test_report_accepts_the_matching_baseline(runner: CliRunner, tmp_path: Path) -> None:
    own = _analysis_of(runner, tmp_path, _SAAS, "own2.json")
    out = tmp_path / "ok2.md"

    result = runner.invoke(app, ["report", _SAAS, "--level", "deep", "--baseline", str(own), "-o", str(out)])

    assert result.exit_code == 0


# --- `-f pdf` without `--level` ------------------------------------------------------------


def test_report_pdf_without_level_is_a_usage_error(runner: CliRunner, tmp_path: Path) -> None:
    out = tmp_path / "deliverable.pdf"

    result = runner.invoke(app, ["report", _MINIMAL, "-f", "pdf", "-o", str(out)])

    assert result.exit_code == 2


def test_report_pdf_without_level_writes_no_file(runner: CliRunner, tmp_path: Path) -> None:
    """It used to write Markdown bytes into the `.pdf` path and report success."""
    out = tmp_path / "deliverable2.pdf"

    runner.invoke(app, ["report", _MINIMAL, "-f", "pdf", "-o", str(out)])

    assert not out.exists()


def test_report_pdf_without_level_names_the_missing_flag(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["report", _MINIMAL, "-f", "pdf", "-o", str(tmp_path / "d3.pdf")])

    assert "--level" in _text(result)


def test_report_locale_without_level_is_a_usage_error(runner: CliRunner) -> None:
    result = runner.invoke(app, ["report", _MINIMAL, "--locale", "en"])

    assert result.exit_code == 2


def test_report_baseline_without_level_is_a_usage_error(runner: CliRunner, tmp_path: Path) -> None:
    own = _analysis_of(runner, tmp_path, _MINIMAL, "own3.json")

    result = runner.invoke(app, ["report", _MINIMAL, "--baseline", str(own)])

    assert result.exit_code == 2


def test_report_markdown_without_level_still_works(runner: CliRunner, tmp_path: Path) -> None:
    """`--format markdown` is the default and describes the legacy output truthfully."""
    out = tmp_path / "legacy.md"

    result = runner.invoke(app, ["report", _MINIMAL, "-f", "markdown", "-o", str(out)])

    assert result.exit_code == 0


# --- `--locale` on the PDF branch ----------------------------------------------------------


def _pdf_run(runner: CliRunner, tmp_path: Path, name: str, *args: str) -> tuple[str, Path]:
    pytest.importorskip("xhtml2pdf")
    out = tmp_path / name
    result = runner.invoke(app, ["report", _MINIMAL, "-l", "executive", "-f", "pdf", "-o", str(out), *args])
    assert result.exit_code == 0
    return _text(result), out


def test_report_pdf_says_a_pt_br_locale_was_not_applied(runner: CliRunner, tmp_path: Path) -> None:
    """The flag used to be discarded in silence; `render_premium_html` has no locale support."""
    message, _ = _pdf_run(runner, tmp_path, "pt.pdf", "--locale", "pt-BR")

    assert "--locale pt-BR" in message


def test_report_pdf_locale_notice_points_at_markdown(runner: CliRunner, tmp_path: Path) -> None:
    message, _ = _pdf_run(runner, tmp_path, "pt2.pdf", "--locale", "pt-BR")

    assert "--format markdown" in message


def test_report_pdf_without_a_locale_flag_still_warns(runner: CliRunner, tmp_path: Path) -> None:
    """pt-BR is the documented default, so the default PDF is also not what was asked for."""
    message, _ = _pdf_run(runner, tmp_path, "default.pdf")

    assert "--locale pt-BR" in message


def test_report_pdf_with_locale_en_is_quiet(runner: CliRunner, tmp_path: Path) -> None:
    """`--locale en` is delivered exactly, so there is nothing to disclose."""
    message, _ = _pdf_run(runner, tmp_path, "en.pdf", "--locale", "en")

    assert "--locale" not in message


def test_report_pdf_stays_in_one_language(runner: CliRunner, tmp_path: Path) -> None:
    """Half-translating the PDF would be worse than an English one: the chrome cannot follow."""
    pypdf = pytest.importorskip("pypdf")
    _, out = _pdf_run(runner, tmp_path, "onelang.pdf", "--locale", "pt-BR")
    text = "\n".join(page.extract_text() or "" for page in pypdf.PdfReader(str(out)).pages)

    assert "Executive summary" in text


# --- missing `xhtml2pdf` -------------------------------------------------------------------


@pytest.fixture
def no_xhtml2pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reproduce a bare install: the renderer raises its Portuguese `ImportError`."""

    def _raise(_html: str) -> bytes:
        raise ImportError("PDF requer o pacote opcional: pip install 'open-threat-model[report]'")

    monkeypatch.setattr("otm_cli.application.report_service.html_to_pdf_bytes", _raise)


@pytest.mark.usefixtures("no_xhtml2pdf")
def test_missing_pdf_extra_exits_one(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["report", _MINIMAL, "-l", "executive", "-f", "pdf", "-o", str(tmp_path / "x.pdf")])

    assert result.exit_code == 1


@pytest.mark.usefixtures("no_xhtml2pdf")
def test_missing_pdf_extra_uses_the_standard_error_shape(runner: CliRunner, tmp_path: Path) -> None:
    """It was the one Portuguese message in an otherwise English CLI, with no Failure/Next step."""
    result = runner.invoke(app, ["report", _MINIMAL, "-l", "executive", "-f", "pdf", "-o", str(tmp_path / "y.pdf")])

    assert "Next step:" in _text(result)


@pytest.mark.usefixtures("no_xhtml2pdf")
def test_missing_pdf_extra_message_is_english(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["report", _MINIMAL, "-l", "executive", "-f", "pdf", "-o", str(tmp_path / "z.pdf")])

    assert "requer o pacote opcional" not in _text(result)
