"""Round-4 regressions: the CLI must not answer a wrong question, and must not answer in
framework language.

Three defects of the same family, each reproduced against the shipped binary before the fix:

* `otm explain` accepted *any* JSON object and reported "No explanations in this file." with exit
  0 for a SARIF report, a backlog JSON and `{}` — telling the user their analysis carries no
  explainability when the truth is that the file is not an analysis. Every sibling consumer of the
  same artifact (`report --analysis-json`, `backlog`, `diff-analysis`) rejects those files.
* `otm templates list --complexity bogus` printed the catalog header and nothing else, exit 0, so
  a wrong filter value and an empty catalog were indistinguishable. `--group-by`, `--level`,
  `--format` and `--methodology` all reject an unknown value with exit 2.
* `otm backlog` and `otm analyze --rules` pasted the raw Pydantic dump — `[type=missing,
  input_value=...]` and the `errors.pydantic.dev` URL — into the user-facing `Likely cause:` slot,
  and `backlog` then printed the same two errors a second time in the polished list below it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from otm_cli.cli import app
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"

#: Fragments that only ever come from Pydantic's own `__str__`, never from this CLI's formatter.
_PYDANTIC_TELLS = ("errors.pydantic.dev", "input_value=", "input_type=", "[type=")


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _wide_console(monkeypatch: pytest.MonkeyPatch) -> None:
    """Rich wraps at the terminal width; a narrow default would split the strings under assert."""
    monkeypatch.setenv("COLUMNS", "300")


def _out(result) -> str:  # noqa: ANN001 - typer's Result type is not exported
    return (result.stdout or "") + (result.stderr or "")


def _analysis_json(tmp_path: Path) -> Path:
    from otm_core_schema import load_document_from_yaml_path
    from otm_threat_engine import analyze_document

    result = analyze_document(load_document_from_yaml_path(_MINIMAL))
    p = tmp_path / "analysis.json"
    p.write_text(json.dumps(result.model_dump(mode="json"), ensure_ascii=False), encoding="utf-8")
    return p


# --------------------------------------------------------------------------------------------
# `otm explain` — a file that is not an analysis must be named as such
# --------------------------------------------------------------------------------------------


def test_explain_rejects_a_sarif_file_instead_of_calling_it_empty(runner: CliRunner, tmp_path: Path) -> None:
    """The exact confusion reported: `--sarif-out` output fed to `explain`."""
    sarif = tmp_path / "out.sarif"
    r_analyze = runner.invoke(app, ["analyze", str(_MINIMAL), "-q", "--sarif-out", str(sarif)])
    assert r_analyze.exit_code == 0

    r = runner.invoke(app, ["explain", str(sarif)])
    out = _out(r)
    assert r.exit_code == 1, out
    assert "No explanations in this file." not in out, "a SARIF report was reported as an analysis with no explanations"
    assert "otm analyze --json-out" in out, "the message must point at the artifact that does work"


def test_explain_rejects_a_backlog_json(runner: CliRunner, tmp_path: Path) -> None:
    backlog = tmp_path / "bl.json"
    r_backlog = runner.invoke(app, ["backlog", str(_MINIMAL), "-f", "json", "-o", str(backlog)])
    assert r_backlog.exit_code == 0

    r = runner.invoke(app, ["explain", str(backlog)])
    out = _out(r)
    assert r.exit_code == 1, out
    assert "No explanations in this file." not in out


def test_explain_rejects_an_empty_object(runner: CliRunner, tmp_path: Path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text("{}", encoding="utf-8")

    r = runner.invoke(app, ["explain", str(empty)])
    out = _out(r)
    assert r.exit_code == 1, out
    assert "No explanations in this file." not in out


def test_explain_still_reads_a_hand_written_explanations_file(runner: CliRunner, tmp_path: Path) -> None:
    """The documented escape hatch stays open: a file that *is* explanations needs no markers."""
    hand = tmp_path / "hand.json"
    hand.write_text(
        json.dumps({"explanations": [{"category": "risk", "subject": "api", "message": "why"}]}),
        encoding="utf-8",
    )

    r = runner.invoke(app, ["explain", str(hand)])
    out = _out(r)
    assert r.exit_code == 0, out
    assert "why" in out


def test_explain_still_says_empty_for_a_real_analysis_with_no_explanations(runner: CliRunner, tmp_path: Path) -> None:
    """The message keeps its one truthful use: a real analysis whose explanations list is empty."""
    path = _analysis_json(tmp_path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["explanations"] = []
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")

    r = runner.invoke(app, ["explain", str(path)])
    out = _out(r)
    assert r.exit_code == 0, out
    assert "No explanations in this file." in out


def test_explain_still_reads_a_real_analysis(runner: CliRunner, tmp_path: Path) -> None:
    r = runner.invoke(app, ["explain", str(_analysis_json(tmp_path))])
    out = _out(r)
    assert r.exit_code == 0, out
    assert "No explanations in this file." not in out


def test_explain_does_not_refuse_a_plain_structural_diff(runner: CliRunner, tmp_path: Path) -> None:
    """`otm diff --json-out` without `--with-analysis` writes a bare `ThreatModelDiff`.

    It carries no explanations and never will — the model has no such field — so "no explanations
    in this file" is the true answer. Refusing it would tell the user that a file this very
    product had just written was not a comparison, which is the guard overreaching.
    """
    diff_json = tmp_path / "d.json"
    r_diff = runner.invoke(
        app, ["diff", str(_MINIMAL), str(_MINIMAL), "-f", "json", "--json-out", str(diff_json), "--summary-only"]
    )
    assert r_diff.exit_code == 0, _out(r_diff)

    r = runner.invoke(app, ["explain", str(diff_json), "--from", "compare"])
    out = _out(r)
    assert r.exit_code == 0, out
    assert "No explanations in this file." in out


def test_explain_still_reads_a_with_analysis_diff(runner: CliRunner, tmp_path: Path) -> None:
    """The `--with-analysis` payload is the flavour that does carry explanations."""
    diff_json = tmp_path / "d2.json"
    r_diff = runner.invoke(
        app,
        [
            "diff",
            str(_MINIMAL),
            str(_MINIMAL),
            "--with-analysis",
            "-f",
            "json",
            "--json-out",
            str(diff_json),
            "--summary-only",
        ],
    )
    assert r_diff.exit_code == 0, _out(r_diff)

    r = runner.invoke(app, ["explain", str(diff_json), "--from", "compare"])
    out = _out(r)
    assert r.exit_code == 0, out
    assert "not an analysis or comparison" not in out


# --------------------------------------------------------------------------------------------
# `otm templates list` — an unknown filter value is a usage error, an empty result says so
# --------------------------------------------------------------------------------------------


def test_templates_list_rejects_an_unknown_complexity(runner: CliRunner) -> None:
    r = runner.invoke(app, ["templates", "list", "--complexity", "bogus"])
    out = _out(r)
    assert r.exit_code == 2, out
    assert "is not one of" in out
    assert "'low'" in out and "'medium'" in out and "'high'" in out


def test_templates_list_still_filters_by_a_valid_complexity(runner: CliRunner) -> None:
    r = runner.invoke(app, ["templates", "list", "--complexity", "medium"])
    out = _out(r)
    assert r.exit_code == 0, out
    assert "otm init -t" in out, "the catalog header must still be printed for a matching filter"


def test_templates_list_says_when_a_filter_matches_nothing(runner: CliRunner) -> None:
    """`--query zzzzz` printed a bare header, so 'wrong value' and 'no match' looked the same."""
    r = runner.invoke(app, ["templates", "list", "--query", "zzzzz"])
    out = _out(r)
    assert r.exit_code == 0, out
    assert "No templates match" in out


def test_templates_list_says_when_an_unknown_category_matches_nothing(runner: CliRunner) -> None:
    r = runner.invoke(app, ["templates", "list", "--category", "nope"])
    out = _out(r)
    assert r.exit_code == 0, out
    assert "No templates match" in out


def test_templates_bare_group_still_lists_the_catalog(runner: CliRunner) -> None:
    r = runner.invoke(app, ["templates"])
    out = _out(r)
    assert r.exit_code == 0, out
    assert "No templates match" not in out


# --------------------------------------------------------------------------------------------
# Pydantic internals must not reach the user, and one failure must be printed once
# --------------------------------------------------------------------------------------------


def test_backlog_reports_a_broken_analysis_without_pydantic_internals(runner: CliRunner, tmp_path: Path) -> None:
    empty = tmp_path / "empty.json"
    empty.write_text("{}", encoding="utf-8")

    r = runner.invoke(app, ["backlog", str(empty), "-d", str(_MINIMAL), "-o", str(tmp_path / "y.md")])
    out = _out(r)
    assert r.exit_code == 1, out
    for tell in _PYDANTIC_TELLS:
        assert tell not in out, f"raw Pydantic text `{tell}` reached the user"
    # The same missing field must be reported once, not once raw and once formatted.
    assert out.count("engine_version") == 1, out
    assert "[engine_version] Field required" in out, "the actionable field list must survive"


def test_analyze_rules_reports_a_bad_field_without_pydantic_internals(runner: CliRunner, tmp_path: Path) -> None:
    rules = tmp_path / "bad-rules.yaml"
    rules.write_text(
        "id: acme\n"
        "rules:\n"
        "  - id: r1\n"
        '    title: "Admin ops need approval"\n'
        "    stride: elevation_of_privilege\n"
        "    match:\n"
        "      component:\n"
        "        suports_admin_operations: true\n",
        encoding="utf-8",
    )

    r = runner.invoke(app, ["analyze", str(_MINIMAL), "-q", "--rules", str(rules)])
    out = _out(r)
    assert r.exit_code == 1, out
    for tell in _PYDANTIC_TELLS:
        assert tell not in out, f"raw Pydantic text `{tell}` reached the user"
    # docs/features/CUSTOM_RULES.md promises the list of valid fields; it must not be lost.
    assert "suports_admin_operations" in out
    assert "supports_admin_operations" in out


def test_analyze_rules_still_reports_a_plain_loader_error(runner: CliRunner, tmp_path: Path) -> None:
    """A non-Pydantic `ValueError` from the loader keeps its own wording."""
    rules = tmp_path / "not-a-mapping.yaml"
    rules.write_text("- just\n- a\n- list\n", encoding="utf-8")

    r = runner.invoke(app, ["analyze", str(_MINIMAL), "-q", "--rules", str(rules)])
    out = _out(r)
    assert r.exit_code == 1, out
    assert "mapping" in out.lower()
