"""Rich must never eat — or execute — text that came from the user's document.

The CLI prints document titles, Pydantic field paths, panel section headers and file paths
through a Rich console. Rich reads `[...]` in a printed string as a style tag, so
`Checkout [v2] rollout` came out as `Checkout  rollout`, the field path in
`  • [components → 0 → id] ...` disappeared entirely, and `Ledger [bold red]PROD` let the
document restyle the tool's own output. Everything user-authored must survive verbatim.

`COLUMNS` is pinned wide in these tests: Rich word-wraps at the terminal width, and a wrapped
line would break the literal `in output` assertions for reasons unrelated to the defect.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
import typer
from otm_cli.cli import app
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.errors import CliUserError
from rich.console import Console
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"

_ID_PATTERN = "^[a-zA-Z0-9_][a-zA-Z0-9_.-]*$"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _wide_console(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "300")


def _out(result: object) -> str:
    stdout = getattr(result, "stdout", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    return stdout + stderr


def _model(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


def _titled(tmp_path: Path, name: str, title: str) -> Path:
    return _model(
        tmp_path,
        name,
        "model:\n"
        '  schema_version: "1.1.0"\n'
        "  system_type: web_application\n"
        "metadata:\n"
        f'  title: "{title}"\n'
        "components:\n"
        "  - id: api\n"
        '    name: "API"\n'
        "    kind: process\n"
        "data_flows: []\n",
    )


# --- schema-validation detail --------------------------------------------------------------


def test_schema_error_keeps_the_field_path_and_the_id_pattern(runner: CliRunner, tmp_path: Path) -> None:
    """The most common authoring mistake: a space in an entity id."""
    bad = _model(
        tmp_path,
        "bad_id.otm.yaml",
        "model:\n"
        '  schema_version: "1.1.0"\n'
        "  system_type: web_application\n"
        "metadata:\n"
        '  title: "Bad id"\n'
        "components:\n"
        '  - id: "A B"\n'
        '    name: "A"\n'
        "    kind: process\n"
        "data_flows: []\n",
    )
    r = runner.invoke(app, ["validate", str(bad)])
    out = _out(r)
    assert r.exit_code == 1
    assert "components" in out, "the field path was swallowed as a Rich style tag"
    assert _ID_PATTERN in out, "the character classes were swallowed as Rich style tags"


def test_schema_error_keeps_the_field_path_for_a_bad_enum(runner: CliRunner, tmp_path: Path) -> None:
    bad = _model(
        tmp_path,
        "bad_enum.otm.yaml",
        "model:\n"
        '  schema_version: "1.1.0"\n'
        "  system_type: web_application\n"
        "metadata:\n"
        '  title: "Bad enum"\n'
        "components:\n"
        "  - id: api\n"
        '    name: "API"\n'
        "    kind: not_a_real_kind\n"
        "data_flows: []\n",
    )
    r = runner.invoke(app, ["validate", str(bad)])
    out = _out(r)
    assert r.exit_code == 1
    assert "components" in out
    assert "kind" in out
    assert "datastore" in out, "the expected-values list must survive"


def test_exit_on_cli_error_renders_bracketed_text_verbatim() -> None:
    buf = io.StringIO()
    console = Console(file=buf, width=300, color_system=None, legacy_windows=False)
    exc = CliUserError(
        exit_code=1,
        failed="validation of `[draft]/m.otm.yaml`.",
        cause="the document is not valid.",
        next_step="fix `[components → 0 → id]`.",
        validation_detail="  • [components → 0 → id] must match '[a-z]+'",
    )
    with pytest.raises(typer.Exit):
        exit_on_cli_error(console, exc)
    text = buf.getvalue()
    assert "[draft]/m.otm.yaml" in text
    assert "[components → 0 → id]" in text
    assert "'[a-z]+'" in text


# --- document titles -----------------------------------------------------------------------


def test_validate_prints_a_bracketed_title_verbatim(runner: CliRunner, tmp_path: Path) -> None:
    model = _titled(tmp_path, "brk.otm.yaml", "Checkout [v2] rollout")
    r = runner.invoke(app, ["validate", str(model)])
    assert r.exit_code == 0
    assert "Checkout [v2] rollout" in _out(r)


def test_analyze_prints_a_bracketed_title_verbatim(runner: CliRunner, tmp_path: Path) -> None:
    model = _titled(tmp_path, "brk.otm.yaml", "Checkout [v2] rollout")
    r = runner.invoke(app, ["analyze", str(model)])
    assert r.exit_code == 0
    assert "Checkout [v2] rollout" in _out(r)


def test_a_style_tag_in_the_title_is_not_executed(runner: CliRunner, tmp_path: Path) -> None:
    """Document content must not control the terminal rendering of the tool's own output."""
    model = _titled(tmp_path, "styled.otm.yaml", "Ledger [bold red]PROD")
    r = runner.invoke(app, ["validate", str(model)])
    assert r.exit_code == 0
    assert "Ledger [bold red]PROD" in _out(r)


# --- panels built from document content ------------------------------------------------------


def test_diff_panel_keeps_its_bracketed_section_headers(runner: CliRunner, tmp_path: Path) -> None:
    """`_field_section_lines` emits `[metadata]`; Rich was deleting the whole header."""
    baseline = _MINIMAL
    revised = tmp_path / "revised.otm.yaml"
    revised.write_text(
        baseline.read_text(encoding="utf-8").replace(
            'title: "Exemplo — API de pedidos"',
            'title: "Exemplo [v2] — API de pedidos"',
        ),
        encoding="utf-8",
    )
    r = runner.invoke(app, ["diff", str(baseline), str(revised)])
    out = _out(r)
    assert r.exit_code == 0
    assert "[metadata]" in out, "the diff section header was parsed as a style tag"
    assert "Exemplo [v2] — API de pedidos" in out


def test_explain_prints_bracketed_subjects_verbatim(runner: CliRunner, tmp_path: Path) -> None:
    payload = {
        "explanations": [
            {"category": "risk", "subject": "svc [prod]", "message": "matches '[a-z]+' rule"},
        ]
    }
    p = tmp_path / "an.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    r = runner.invoke(app, ["explain", str(p)])
    out = _out(r)
    assert r.exit_code == 0
    assert "svc [prod]" in out
    assert "'[a-z]+'" in out
