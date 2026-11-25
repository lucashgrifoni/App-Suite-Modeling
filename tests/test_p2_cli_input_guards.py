"""Phase-2 regressions for CLI inputs that produced a traceback or were silently ignored.

* `otm backlog x.json` raw-tracebacked on a missing file, on a directory and on non-UTF-8
  content — while `otm backlog x.otm.yaml`, the YAML branch of the very same command, handled
  all three cleanly. `otm explain` had the non-UTF-8 half of the same gap.
* `otm import openapi` / `otm import k8s` raw-tracebacked on an empty or malformed artifact,
  while `otm import otm` produced the standard three-line error for identical input.
* `otm backlog --group-by` accepted any string and quietly fell back to the default grouping,
  unlike `--format`, `--methodology`, `--level` and every other enum option.

`docs/CI_AND_SECURITY_EVIDENCE.md` lists "YAML inválido" and an inaccessible read as exit-1 CLI
user errors, so the tracebacks contradicted a stated contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from click.testing import Result
from otm_cli.cli import app
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = str(_ROOT / "examples" / "minimal.otm.yaml")
_SAAS = str(_ROOT / "examples" / "saas-ordering-v1.otm.yaml")

_LATIN1_JSON = '{"document_title":"Análise"}'
_BROKEN_YAML = "a: [1, 2\nb: {"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _out(result: Result) -> str:
    return (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")


def _latin1(tmp_path: Path, name: str) -> Path:
    path = tmp_path / name
    path.write_bytes(_LATIN1_JSON.encode("iso-8859-1"))
    return path


def _analysis(runner: CliRunner, tmp_path: Path, name: str) -> Path:
    out = tmp_path / name
    assert runner.invoke(app, ["analyze", _MINIMAL, "--json-out", str(out), "--quiet"]).exit_code == 0
    return out


# --- `otm backlog` reading analysis JSON ----------------------------------------------------


def test_backlog_on_a_missing_json_exits_one(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["backlog", str(tmp_path / "does_not_exist.json")])

    assert result.exit_code == 1


def test_backlog_on_a_missing_json_does_not_traceback(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["backlog", str(tmp_path / "does_not_exist.json")])

    assert not isinstance(result.exception, OSError)


def test_backlog_on_a_missing_json_reports_a_failure(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["backlog", str(tmp_path / "does_not_exist.json")])

    assert "Failure:" in _out(result)


def test_backlog_on_a_directory_named_json_does_not_traceback(runner: CliRunner, tmp_path: Path) -> None:
    folder = tmp_path / "dir.json"
    folder.mkdir()

    result = runner.invoke(app, ["backlog", str(folder)])

    assert not isinstance(result.exception, OSError)


def test_backlog_on_non_utf8_json_does_not_traceback(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["backlog", str(_latin1(tmp_path, "latin1.json"))])

    assert not isinstance(result.exception, UnicodeDecodeError)


def test_backlog_on_non_utf8_json_exits_one(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["backlog", str(_latin1(tmp_path, "latin1b.json"))])

    assert result.exit_code == 1


def test_backlog_still_reports_malformed_json(runner: CliRunner, tmp_path: Path) -> None:
    """The pre-existing JSONDecodeError branch must keep its wording."""
    broken = tmp_path / "broken.json"
    broken.write_text("{ not json", encoding="utf-8")

    result = runner.invoke(app, ["backlog", str(broken)])

    assert "invalid JSON" in _out(result)


def test_backlog_still_works_on_a_good_analysis(runner: CliRunner, tmp_path: Path) -> None:
    analysis = _analysis(runner, tmp_path, "good.json")

    result = runner.invoke(app, ["backlog", str(analysis)])

    assert result.exit_code == 0


# --- `otm backlog --document` pairing -------------------------------------------------------


def test_backlog_refuses_a_document_from_another_system(runner: CliRunner, tmp_path: Path) -> None:
    """Same defect as `otm report --analysis-json`: `-d` only resolves names, and was unchecked."""
    foreign = _analysis(runner, tmp_path, "foreign.json")

    result = runner.invoke(app, ["backlog", str(foreign), "-d", _SAAS])

    assert result.exit_code == 1


def test_backlog_document_mismatch_names_the_flag(runner: CliRunner, tmp_path: Path) -> None:
    foreign = _analysis(runner, tmp_path, "foreign2.json")

    result = runner.invoke(app, ["backlog", str(foreign), "-d", _SAAS])

    assert "--document" in _out(result)


def test_backlog_accepts_the_matching_document(runner: CliRunner, tmp_path: Path) -> None:
    own = _analysis(runner, tmp_path, "own.json")

    result = runner.invoke(app, ["backlog", str(own), "-d", _MINIMAL])

    assert result.exit_code == 0


# --- `otm explain` reading analysis JSON ----------------------------------------------------


def test_explain_on_non_utf8_json_does_not_traceback(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["explain", str(_latin1(tmp_path, "latin1c.json"))])

    assert not isinstance(result.exception, UnicodeDecodeError)


def test_explain_on_non_utf8_json_exits_one(runner: CliRunner, tmp_path: Path) -> None:
    result = runner.invoke(app, ["explain", str(_latin1(tmp_path, "latin1d.json"))])

    assert result.exit_code == 1


def test_explain_on_a_directory_does_not_traceback(runner: CliRunner, tmp_path: Path) -> None:
    folder = tmp_path / "expl.json"
    folder.mkdir()

    result = runner.invoke(app, ["explain", str(folder)])

    assert not isinstance(result.exception, OSError)


# --- `otm import openapi` / `otm import k8s` ------------------------------------------------


def test_import_openapi_on_an_empty_file_does_not_traceback(runner: CliRunner, tmp_path: Path) -> None:
    empty = tmp_path / "empty.yaml"
    empty.write_text("", encoding="utf-8")

    result = runner.invoke(app, ["import", "openapi", str(empty)])

    assert not isinstance(result.exception, ValueError)


def test_import_openapi_on_an_empty_file_exits_one(runner: CliRunner, tmp_path: Path) -> None:
    empty = tmp_path / "empty2.yaml"
    empty.write_text("", encoding="utf-8")

    result = runner.invoke(app, ["import", "openapi", str(empty)])

    assert result.exit_code == 1


def test_import_openapi_on_an_empty_file_names_the_next_step(runner: CliRunner, tmp_path: Path) -> None:
    """`otm import otm` already answers identical input with the three-line error."""
    empty = tmp_path / "empty3.yaml"
    empty.write_text("", encoding="utf-8")

    result = runner.invoke(app, ["import", "openapi", str(empty)])

    assert "Next step:" in _out(result)


def test_import_openapi_on_malformed_json_does_not_traceback(runner: CliRunner, tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ not json", encoding="utf-8")

    result = runner.invoke(app, ["import", "openapi", str(bad)])

    assert not isinstance(result.exception, ValueError)


def test_import_k8s_on_malformed_yaml_does_not_traceback(runner: CliRunner, tmp_path: Path) -> None:
    bad = tmp_path / "bad2.yaml"
    bad.write_text(_BROKEN_YAML, encoding="utf-8")

    result = runner.invoke(app, ["import", "k8s", str(bad)])

    assert not isinstance(result.exception, yaml.YAMLError)


def test_import_k8s_on_malformed_yaml_exits_one(runner: CliRunner, tmp_path: Path) -> None:
    bad = tmp_path / "bad3.yaml"
    bad.write_text(_BROKEN_YAML, encoding="utf-8")

    result = runner.invoke(app, ["import", "k8s", str(bad)])

    assert result.exit_code == 1


def test_import_terraform_on_binary_input_does_not_traceback(runner: CliRunner, tmp_path: Path) -> None:
    """Terraform shares the importer wrapper, so it gets the same guard."""
    bad = tmp_path / "bad.tf"
    bad.write_bytes(b"\x00\x01\x02\xff\xfe\xfd")

    result = runner.invoke(app, ["import", "terraform", str(bad)])

    assert not isinstance(result.exception, ValueError)


def test_import_openapi_still_works_on_a_valid_spec(runner: CliRunner, tmp_path: Path) -> None:
    spec = tmp_path / "orders.yaml"
    spec.write_text(
        "openapi: 3.0.0\ninfo:\n  title: Orders API\n  version: '1.0.0'\npaths:\n"
        "  /orders:\n    get:\n      operationId: listOrders\n",
        encoding="utf-8",
    )

    result = runner.invoke(app, ["import", "openapi", str(spec), "-o", str(tmp_path / "draft.otm.yaml")])

    assert result.exit_code == 0


# --- `otm backlog --group-by` ---------------------------------------------------------------


def test_backlog_rejects_an_unknown_group_by(runner: CliRunner) -> None:
    result = runner.invoke(app, ["backlog", _MINIMAL, "--group-by", "bogus"])

    assert result.exit_code == 2


def test_backlog_rejects_an_empty_group_by(runner: CliRunner) -> None:
    result = runner.invoke(app, ["backlog", _MINIMAL, "--group-by", ""])

    assert result.exit_code == 2


def test_backlog_group_by_error_lists_the_valid_values(runner: CliRunner) -> None:
    result = runner.invoke(app, ["backlog", _MINIMAL, "--group-by", "categry"])

    assert "root-cause" in _out(result)


@pytest.mark.parametrize("value", ["root-cause", "control", "category"])
def test_backlog_accepts_every_documented_group_by(runner: CliRunner, value: str) -> None:
    result = runner.invoke(app, ["backlog", _MINIMAL, "--group-by", value])

    assert result.exit_code == 0


def test_backlog_group_by_category_still_differs_from_the_default(runner: CliRunner, tmp_path: Path) -> None:
    """Proves the accepted values still reach the renderer rather than all collapsing."""
    default = tmp_path / "default.md"
    category = tmp_path / "category.md"
    runner.invoke(app, ["backlog", _MINIMAL, "-o", str(default)])
    runner.invoke(app, ["backlog", _MINIMAL, "--group-by", "category", "-o", str(category)])

    assert default.read_text(encoding="utf-8") != category.read_text(encoding="utf-8")
