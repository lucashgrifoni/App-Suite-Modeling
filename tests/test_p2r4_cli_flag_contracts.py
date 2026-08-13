"""Round-4 regressions on what the CLI accepts and what it writes about itself.

* `otm report --locale` was typed as a free string and resolved with a server-style fallback, so
  every unrecognised value silently produced an **English** report with exit 0. `--locale ptBR` —
  the obvious typo, from exactly the audience the `pt-BR` default is for — therefore gave a
  different language from the one the same command gives with no flag at all.
* SARIF `artifactLocation.uri` was written with raw spaces. SARIF 2.1.0 defines that field as a
  URI reference per RFC 3986, whose character set has no space, and a path with a space is the
  normal case on Windows — the repository this ships from lives under one.
* The README's "Exit codes, for scripting" list named `0`, `1` and `3` and omitted `2`, which the
  CLI returns for every bad flag or bad flag value, so a pipeline written from the README treats
  the most common failure as an unknown state.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from otm_cli.cli import app
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"
_README = _ROOT / "README.md"

_PT_HEADING = "## Capa executiva"
_EN_HEADING = "## Executive cover"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _wide_console(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "300")


def _out(result) -> str:  # noqa: ANN001 - typer's Result type is not exported
    return (result.stdout or "") + (result.stderr or "")


def _report(runner: CliRunner, tmp_path: Path, *extra: str) -> tuple[int, str, str]:
    """Run `otm report -l executive` and return (exit code, output, report text)."""
    out_file = tmp_path / "loc.md"
    out_file.unlink(missing_ok=True)
    r = runner.invoke(app, ["report", str(_MINIMAL), "-l", "executive", "-o", str(out_file), *extra])
    text = out_file.read_text(encoding="utf-8") if out_file.exists() else ""
    return r.exit_code, _out(r), text


# --------------------------------------------------------------------------------------------
# `--locale`
# --------------------------------------------------------------------------------------------


@pytest.mark.parametrize("locale", ["ptBR", "ptbr", "portuguese", "br", "fr", "xx", "espanol"])
def test_an_unrecognised_locale_is_refused_instead_of_silently_switching_language(
    runner: CliRunner, tmp_path: Path, locale: str
) -> None:
    code, out, text = _report(runner, tmp_path, "--locale", locale)

    assert code == 2, out
    assert "is not one of" in out and "pt-BR" in out
    assert text == "", "a refused run must not leave a report behind"


@pytest.mark.parametrize("locale", ["pt-BR", "pt_BR", "pt-br", "PT-BR", "pt", "pt-PT", ""])
def test_every_portuguese_tag_still_renders_portuguese(runner: CliRunner, tmp_path: Path, locale: str) -> None:
    code, out, text = _report(runner, tmp_path, "--locale", locale)

    assert code == 0, out
    assert _PT_HEADING in text


@pytest.mark.parametrize("locale", ["en", "en-US", "EN"])
def test_every_english_tag_still_renders_english(runner: CliRunner, tmp_path: Path, locale: str) -> None:
    code, out, text = _report(runner, tmp_path, "--locale", locale)

    assert code == 0, out
    assert _EN_HEADING in text


def test_omitting_the_flag_matches_the_documented_default(runner: CliRunner, tmp_path: Path) -> None:
    """The bug's sharpest edge: a typo used to give a *different* language from no flag at all."""
    code_default, out_default, text_default = _report(runner, tmp_path)
    code_explicit, _, text_explicit = _report(runner, tmp_path, "--locale", "pt-BR")

    assert code_default == 0, out_default
    assert code_explicit == 0
    assert _PT_HEADING in text_default
    assert text_default == text_explicit


def test_the_server_side_resolver_keeps_its_forgiving_fallback() -> None:
    """The API must not start rejecting an optional field; only the CLI got stricter."""
    from otm_exporters.export_locale import normalize_export_locale, recognized_export_locale

    assert normalize_export_locale("ptBR") == "en"
    assert normalize_export_locale(None) == "pt-BR"
    assert recognized_export_locale("ptBR") is None
    assert recognized_export_locale("pt-PT") == "pt-BR"


# --------------------------------------------------------------------------------------------
# SARIF `artifactLocation.uri`
# --------------------------------------------------------------------------------------------


def _sarif_uris(sarif_path: Path) -> set[str]:
    data = json.loads(sarif_path.read_text(encoding="utf-8"))
    return {
        loc["physicalLocation"]["artifactLocation"]["uri"]
        for run in data["runs"]
        for result in run["results"]
        for loc in result["locations"]
    }


def test_a_model_path_with_spaces_is_percent_encoded(runner: CliRunner, tmp_path: Path) -> None:
    nested = tmp_path / "sub dir" / "deep"
    nested.mkdir(parents=True)
    model = nested / "my model.otm.yaml"
    model.write_text(_MINIMAL.read_text(encoding="utf-8"), encoding="utf-8")
    sarif = tmp_path / "s.sarif"

    r = runner.invoke(app, ["analyze", str(model), "-q", "--sarif-out", str(sarif)])
    assert r.exit_code == 0, _out(r)

    uris = _sarif_uris(sarif)
    assert uris, "the fixture must produce at least one located result"
    for uri in uris:
        assert " " not in uri, f"`{uri}` is not a URI reference: RFC 3986 has no space"
        assert "%20" in uri
        assert "\\" not in uri, "backslashes must stay normalised to `/`"


def test_a_plain_path_is_not_over_encoded(runner: CliRunner, tmp_path: Path) -> None:
    """`/` is the segment separator and must survive; encoding it would break every consumer."""
    nested = tmp_path / "models"
    nested.mkdir()
    model = nested / "api.otm.yaml"
    model.write_text(_MINIMAL.read_text(encoding="utf-8"), encoding="utf-8")
    sarif = tmp_path / "s.sarif"

    r = runner.invoke(app, ["analyze", str(model), "-q", "--sarif-out", str(sarif)])
    assert r.exit_code == 0, _out(r)

    for uri in _sarif_uris(sarif):
        assert uri.endswith("models/api.otm.yaml"), uri
        assert "%2F" not in uri


# --------------------------------------------------------------------------------------------
# The documented exit-code contract
# --------------------------------------------------------------------------------------------


def test_the_readme_documents_the_exit_code_the_cli_actually_returns(runner: CliRunner) -> None:
    r = runner.invoke(app, ["analyze", str(_MINIMAL), "-q", "--methodology", "bogus"])
    assert r.exit_code == 2, _out(r)

    line = next(ln for ln in _README.read_text(encoding="utf-8").splitlines() if "Exit codes, for scripting" in ln)
    for code in ("`0`", "`1`", "`2`", "`3`"):
        assert code in line, f"the README exit-code contract omits {code}: {line}"
