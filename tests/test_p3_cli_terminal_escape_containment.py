"""Document text must not be able to drive the terminal the CLI is writing to.

`safe()` solved exactly one of the two escaping problems on the Rich surface. It calls
`rich.markup.escape`, which neutralises `[bold red]` — and Rich's own `strip_control_codes` list
is `[7, 8, 11, 12, 13]` (BEL, BS, VT, FF, CR), which deliberately excludes ESC (0x1B). So an
unconstrained document string reached the terminal with its CSI sequences intact:

    metadata.title: "OK\\e[2K\\e[G\\e[31mFAKE ERROR\\e[0m"
    $ otm validate ansi.otm.yaml
    | Title: OK^[[2K^[[G^[[31mFAKE ERROR^[[0m |     <- 4 raw ESC bytes on the wire

That is not cosmetic. `.pre-commit-hooks.yaml` ships `entry: otm validate`, and pre-commit hands
the hook every matching path at once, so `otm validate a.otm.yaml b.otm.yaml` prints one block per
file — a title in the *second* file carrying `\\e[1A\\e[2K` pairs walks the cursor back over the
*first* file's `Invalid` block and repaints it. Measured before the fix: 35 raw ESC bytes and a
forged `All 2 files valid.` while the process still exited 1. What is forged is the text the
developer reads to decide what went wrong — the same asset the Markdown (T2) and PDF (I5)
renderers already protect, with the terminal renderer simply never modelled.

Two properties are pinned here, and the second matters as much as the first:

* **Neutralisation, not truncation.** The literal text around the escape must survive. A fix that
  dropped the whole value would pass an "no ESC in output" assertion and destroy the diagnostic.
* **Only control characters go.** `safe()` has legitimate multi-line consumers — `precheck` panels
  a `json.dumps(..., indent=2)`, `diff-analysis` panels a `"\\n".join(lines)`, `handle_errors`
  panels a multi-line `validation_detail`. Flattening line breaks inside `safe()` (which the
  original fix proposal suggested) would trade this defect for its mirror image: legitimate output
  collapsed onto one line. TAB and LF are therefore kept, and there are tests below that fail if
  someone removes them.

C1 is in the strip set alongside C0: in UTF-8 mode a terminal that honours 8-bit controls reads
U+009B as CSI, so an ESC-only filter is bypassed by one codepoint. U+0080-U+009F carry no text.

The Markdown and JSON surfaces were checked at the same time and were already clean —
`otm export -f md`, `otm report` and `otm backlog` carry the same hostile component names with
zero ESC bytes, because `otm_exporters.markdown_text._CONTROL_CHARS` already strips them there.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml
from otm_cli.cli import app
from otm_cli.shared.render import safe
from typer.testing import CliRunner

#: Everything a terminal reads as a command rather than as text: C0 minus TAB/LF, DEL, and C1.
#: TAB and LF are absent on purpose — they are legitimate whitespace on this surface.
_TERMINAL_CONTROLS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")

#: The literal the payload wraps. Its presence proves the value was neutralised and not dropped.
_MARKER = "FAKE ERROR"

#: One entry per way of steering a terminal from inside a string.
_PAYLOADS = {
    "csi-erase-line": "\x1b[2K\x1b[G",
    "csi-cursor-up": "\x1b[1A\x1b[2K\x1b[1A\x1b[2K",
    "sgr-colour": "\x1b[31m",
    "osc-52-clipboard": "\x1b]52;c;ZXZpbA==\x1b\\",
    "c1-csi-8bit": "\x9b2K\x9bG",
    "nul": "\x00",
}


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _wide_console(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rich wraps at the terminal width; a wrapped line would break the literal assertions."""
    monkeypatch.setenv("COLUMNS", "300")


def _out(result: object) -> str:
    stdout = getattr(result, "stdout", "") or ""
    stderr = getattr(result, "stderr", "") or ""
    return stdout + stderr


def _document(title: str) -> dict[str, object]:
    return {
        "model": {"schema_version": "1.1.0", "system_type": "web_application"},
        "metadata": {"title": title},
        "components": [
            {"id": "api", "name": "API", "kind": "process"},
            {"id": "db", "name": "DB", "kind": "datastore"},
        ],
        "data_flows": [
            {
                "id": "f1",
                "from_component": "api",
                "to_component": "db",
                "protocol": "TCP",
                "semantic_class": "storage_processing_flow",
            }
        ],
    }


def _write_model(tmp_path: Path, name: str, title: str) -> Path:
    """PyYAML refuses a raw ESC byte in a plain scalar; `safe_dump` emits the `\\e` escape form."""
    path = tmp_path / name
    path.write_text(yaml.safe_dump(_document(title), allow_unicode=True), encoding="utf-8")
    return path


def _hostile_title(payload: str) -> str:
    return f"OK{payload}{_MARKER}{payload}"


def _assert_neutralised(output: str) -> None:
    """No control character reached the terminal, and the text around it still did."""
    leaked = sorted({hex(ord(c)) for c in _TERMINAL_CONTROLS.findall(output)})
    assert leaked == []
    assert _MARKER in output


# --- the hostile direction --------------------------------------------------------------------


@pytest.mark.parametrize("payload", list(_PAYLOADS.values()), ids=list(_PAYLOADS))
def test_validate_neutralises_terminal_controls_in_the_document_title(
    runner: CliRunner, tmp_path: Path, payload: str
) -> None:
    model = _write_model(tmp_path, "hostile.otm.yaml", _hostile_title(payload))
    result = runner.invoke(app, ["validate", str(model)])
    assert result.exit_code == 0
    _assert_neutralised(_out(result))


@pytest.mark.parametrize("payload", list(_PAYLOADS.values()), ids=list(_PAYLOADS))
def test_analyze_neutralises_terminal_controls_in_the_document_title(
    runner: CliRunner, tmp_path: Path, payload: str
) -> None:
    model = _write_model(tmp_path, "hostile.otm.yaml", _hostile_title(payload))
    result = runner.invoke(app, ["analyze", str(model)])
    assert result.exit_code == 0
    _assert_neutralised(_out(result))


@pytest.mark.parametrize("payload", list(_PAYLOADS.values()), ids=list(_PAYLOADS))
def test_diff_neutralises_terminal_controls_in_the_document_title(
    runner: CliRunner, tmp_path: Path, payload: str
) -> None:
    baseline = _write_model(tmp_path, "base.otm.yaml", "Baseline")
    revised = _write_model(tmp_path, "revised.otm.yaml", _hostile_title(payload))
    result = runner.invoke(app, ["diff", str(baseline), str(revised)])
    assert result.exit_code == 0
    _assert_neutralised(_out(result))


def test_the_batch_path_pre_commit_uses_cannot_repaint_an_earlier_file_block(runner: CliRunner, tmp_path: Path) -> None:
    """The reported escalation: file B scrubbing file A's `Invalid` diagnostic."""
    bad = tmp_path / "a_bad.otm.yaml"
    bad.write_text("model: {}\n", encoding="utf-8")
    good = _write_model(tmp_path, "b_good.otm.yaml", _hostile_title("\x1b[1A\x1b[2K" * 16))
    result = runner.invoke(app, ["validate", str(bad), str(good)])
    output = _out(result)
    assert result.exit_code == 1
    assert "\x1b" not in output
    assert "Invalid" in output


# --- the surfaces that were already clean, pinned so they stay that way ------------------------
#
# `otm export -f md`, `otm report` and `otm backlog` write the document's own text to stdout with a
# bare `print()`, so they are the same hazard by a different route. They were measured at the same
# time as the defect above and were already safe — `otm_exporters.markdown_text._CONTROL_CHARS`
# strips ESC there — with the hostile component name, flow name and summary reaching the output
# intact and not one control byte with them. Untested, that stays true only by luck.


@pytest.mark.parametrize("command", ["export", "report", "backlog"])
def test_the_stdout_document_surfaces_carry_no_control_bytes(runner: CliRunner, tmp_path: Path, command: str) -> None:
    model = _write_model(tmp_path, "hostile.otm.yaml", _hostile_title(_PAYLOADS["csi-erase-line"]))
    result = runner.invoke(app, [command, str(model)])
    assert result.exit_code == 0
    _assert_neutralised(_out(result))


# --- the legitimate direction: what the guard must NOT reject ---------------------------------


def test_safe_keeps_tab_and_newline() -> None:
    """`safe()` has multi-line callers; stripping LF here would break `precheck` and `diff`."""
    assert safe("first\tcolumn\nsecond line") == "first\tcolumn\nsecond line"


def test_safe_keeps_bracketed_and_accented_text() -> None:
    """The markup escape still has to run, and non-ASCII text is not a control character."""
    assert safe("Checkout [v2] — ação · 100%") == "Checkout \\[v2] — ação · 100%"


def test_precheck_still_prints_its_json_panel_on_several_lines(runner: CliRunner, tmp_path: Path) -> None:
    """End-to-end proof that the fix did not flatten a legitimate multi-line panel."""
    model = _write_model(tmp_path, "plain.otm.yaml", "Checkout [v2] rollout")
    result = runner.invoke(app, ["precheck", str(model)])
    body = [line for line in _out(result).splitlines() if '"' in line]
    assert result.exit_code == 0
    assert len(body) > 5


def test_validate_still_prints_a_bracketed_title_verbatim(runner: CliRunner, tmp_path: Path) -> None:
    model = _write_model(tmp_path, "plain.otm.yaml", "Checkout [v2] rollout")
    result = runner.invoke(app, ["validate", str(model)])
    assert result.exit_code == 0
    assert "Checkout [v2] rollout" in _out(result)


def test_validate_keeps_a_tab_inside_the_title(runner: CliRunner, tmp_path: Path) -> None:
    """TAB is whitespace an author can type; the guard must let it through."""
    model = _write_model(tmp_path, "tabbed.otm.yaml", "Checkout\tv2")
    result = runner.invoke(app, ["validate", str(model)])
    assert result.exit_code == 0
    assert "Checkout" in _out(result)
