"""Round-4 CLI reproductions: pairing by title was wrong in both directions.

Three reported defects, one cause — `otm report --analysis-json`, `otm report --baseline` and
`otm backlog --document` all identified a model by `metadata.title`:

* **false accept.** `otm init -t <template>` copies the template's title verbatim, so two models
  built from templates share it by construction. Pairing teamB's admin portal with teamA's API
  analysis was accepted, and the report listed teamA's components and threats under teamB's
  name. `otm diff-analysis` refused the identical pair.
* **false accept.** An analysis of an earlier revision of the *same* document carries the same
  title, so it passed. The premium report then inventoried the component added since ("Componentes: 6",
  "Servidor FTP legado") while reporting no threat against it.
* **false refuse.** `--baseline` is an analysis of a previous version by definition, so renaming
  the model between releases — the ordinary case the flag exists for — hard-failed the run and
  produced no report at all, while the API and `diff-analysis` accepted the same pair.

Exit-code contract: 0 = success, 1 = refusal, 2 = flag/usage error.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from click.testing import Result
from otm_cli.cli import app
from typer.testing import CliRunner

_REFUSED = 1

#: Two templates with disjoint entities. `otm init` copies each template's own title, so the
#: collision below is the one a user reaches by editing one line — or by using one template twice.
_TEMPLATE_A = "api-backend"
_TEMPLATE_B = "admin-portal"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _out(result: Result) -> str:
    return (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")


def _init(runner: CliRunner, template: str, path: Path) -> Path:
    result = runner.invoke(app, ["init", str(path), "-t", template])
    assert result.exit_code == 0, _out(result)
    return path


def _analyze(runner: CliRunner, model: Path, out: Path) -> Path:
    result = runner.invoke(app, ["analyze", str(model), "--json-out", str(out), "--quiet"])
    assert result.exit_code == 0, _out(result)
    return out


def _retitle(model: Path, title: str) -> None:
    payload: dict[str, Any] = yaml.safe_load(model.read_text(encoding="utf-8"))
    payload["metadata"]["title"] = title
    model.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")


def _title_of(model: Path) -> str:
    return str(yaml.safe_load(model.read_text(encoding="utf-8"))["metadata"]["title"])


def _append_component(model: Path) -> str:
    """The edit any user makes: one more component, one more flow reaching it."""
    payload: dict[str, Any] = yaml.safe_load(model.read_text(encoding="utf-8"))
    payload["components"].append(
        {
            "id": "legacy_ftp",
            "name": "Servidor FTP legado",
            "kind": "external_entity",
            "handles_sensitive_data": True,
        }
    )
    payload.setdefault("data_flows", []).append(
        {
            "id": "f_legacy",
            "name": "Upload para FTP",
            "from_component": payload["components"][0]["id"],
            "to_component": "legacy_ftp",
            "protocol": "FTP",
            "authenticated": False,
            "encrypted": False,
            "public_exposure": True,
            "supports_file_upload": True,
        }
    )
    model.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return "legacy_ftp"


# --- two models, one template title ------------------------------------------------------------


@pytest.fixture
def crossed(runner: CliRunner, tmp_path: Path) -> tuple[Path, Path]:
    """teamB's model and teamA's analysis, sharing a title the way two templates do."""
    team_a = _init(runner, _TEMPLATE_A, tmp_path / "teamA.otm.yaml")
    team_b = _init(runner, _TEMPLATE_B, tmp_path / "teamB.otm.yaml")
    _retitle(team_b, _title_of(team_a))
    return team_b, _analyze(runner, team_a, tmp_path / "A.analysis.json")


def test_report_refuses_a_foreign_analysis_that_shares_the_title(
    runner: CliRunner, crossed: tuple[Path, Path], tmp_path: Path
) -> None:
    """The report used to carry teamA's api/queue/worker/db threats under teamB's name."""
    team_b, foreign = crossed
    out = tmp_path / "crosspair.md"

    result = runner.invoke(
        app, ["report", str(team_b), "-l", "standard", "--analysis-json", str(foreign), "-o", str(out)]
    )

    assert result.exit_code == _REFUSED, _out(result)


def test_the_cross_pair_report_is_never_written(runner: CliRunner, crossed: tuple[Path, Path], tmp_path: Path) -> None:
    team_b, foreign = crossed
    out = tmp_path / "crosspair2.md"

    runner.invoke(app, ["report", str(team_b), "-l", "standard", "--analysis-json", str(foreign), "-o", str(out)])

    assert not out.exists()


def test_the_refusal_names_the_entities_that_do_not_exist_in_this_model(
    runner: CliRunner, crossed: tuple[Path, Path]
) -> None:
    """A title-only message could not say *why*; the structural one shows the evidence."""
    team_b, foreign = crossed

    result = runner.invoke(app, ["report", str(team_b), "-l", "standard", "--analysis-json", str(foreign)])

    assert "component:" in _out(result)


def test_backlog_refuses_a_foreign_document_that_shares_the_title(
    runner: CliRunner, crossed: tuple[Path, Path]
) -> None:
    """`otm backlog A.analysis.json -d teamB.otm.yaml` relabelled teamA's rows with teamB's names."""
    team_b, foreign = crossed

    result = runner.invoke(app, ["backlog", str(foreign), "-d", str(team_b)])

    assert result.exit_code == _REFUSED, _out(result)


def test_baseline_refuses_a_foreign_analysis_that_shares_the_title(
    runner: CliRunner, crossed: tuple[Path, Path]
) -> None:
    """It produced "ameaças adicionadas 23, removidas 23" from two unrelated systems."""
    team_b, foreign = crossed

    result = runner.invoke(app, ["report", str(team_b), "-l", "deep", "--baseline", str(foreign)])

    assert result.exit_code == _REFUSED, _out(result)


def test_the_baseline_refusal_still_names_the_flag(runner: CliRunner, crossed: tuple[Path, Path]) -> None:
    team_b, foreign = crossed

    result = runner.invoke(app, ["report", str(team_b), "-l", "deep", "--baseline", str(foreign)])

    assert "--baseline" in _out(result)


# --- a stale analysis of the same document -------------------------------------------------------


@pytest.fixture
def stale(runner: CliRunner, tmp_path: Path) -> tuple[Path, Path, str]:
    """One model, analysed, then edited the way a user edits it: revision 1's analysis on disk."""
    model = _init(runner, _TEMPLATE_B, tmp_path / "svc.otm.yaml")
    analysis = _analyze(runner, model, tmp_path / "rev1.analysis.json")
    added = _append_component(model)
    return model, analysis, added


def test_report_refuses_an_analysis_of_the_previous_revision(
    runner: CliRunner, stale: tuple[Path, Path, str], tmp_path: Path
) -> None:
    """It emitted a report that listed the new component and gave it zero threats."""
    model, analysis, _ = stale
    out = tmp_path / "stale.md"

    result = runner.invoke(app, ["report", str(model), "-l", "deep", "--analysis-json", str(analysis), "-o", str(out)])

    assert result.exit_code == _REFUSED, _out(result)


def test_the_stale_refusal_names_the_component_the_analysis_never_saw(
    runner: CliRunner, stale: tuple[Path, Path, str]
) -> None:
    model, analysis, added = stale

    result = runner.invoke(app, ["report", str(model), "-l", "deep", "--analysis-json", str(analysis)])

    assert added in _out(result)


def test_the_stale_refusal_tells_the_user_to_re_run_the_analysis(
    runner: CliRunner, stale: tuple[Path, Path, str]
) -> None:
    """ "Drop the flag" is the wrong advice here: the analysis is right, just old."""
    model, analysis, _ = stale

    result = runner.invoke(app, ["report", str(model), "-l", "deep", "--analysis-json", str(analysis)])

    assert "otm analyze" in _out(result)


def test_backlog_refuses_a_document_newer_than_its_analysis(runner: CliRunner, stale: tuple[Path, Path, str]) -> None:
    """The backlog silently dropped the actions for the component added since."""
    model, analysis, _ = stale

    result = runner.invoke(app, ["backlog", str(analysis), "-d", str(model)])

    assert result.exit_code == _REFUSED, _out(result)


def test_a_refreshed_analysis_of_the_edited_model_is_accepted(
    runner: CliRunner, stale: tuple[Path, Path, str], tmp_path: Path
) -> None:
    """The fix must leave the documented recovery path working."""
    model, _, _ = stale
    fresh = _analyze(runner, model, tmp_path / "rev2.analysis.json")
    out = tmp_path / "fresh.md"

    result = runner.invoke(app, ["report", str(model), "-l", "deep", "--analysis-json", str(fresh), "-o", str(out)])

    assert result.exit_code == 0, _out(result)


# --- a rename between versions is exactly what `--baseline` is for -------------------------------


@pytest.fixture
def renamed_release(runner: CliRunner, tmp_path: Path) -> tuple[Path, Path, Path]:
    """v1 analysed, then the team renames the product in `metadata.title` for v2."""
    model = _init(runner, _TEMPLATE_A, tmp_path / "v.otm.yaml")
    v1 = _analyze(runner, model, tmp_path / "v1.analysis.json")
    _retitle(model, "Orders Platform (formerly async API)")
    v2 = _analyze(runner, model, tmp_path / "v2.analysis.json")
    return model, v1, v2


def test_a_renamed_release_still_accepts_its_baseline(
    runner: CliRunner, renamed_release: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    """The reproduction: exit 1 and no report, for a pair `diff-analysis` and the API both accept."""
    model, v1, v2 = renamed_release
    out = tmp_path / "v2report.md"

    result = runner.invoke(
        app, ["report", str(model), "-l", "deep", "--analysis-json", str(v2), "--baseline", str(v1), "-o", str(out)]
    )

    assert result.exit_code == 0, _out(result)


def test_the_renamed_release_report_is_actually_written(
    runner: CliRunner, renamed_release: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    """The refusal cost the whole report, not just the baseline section."""
    model, v1, v2 = renamed_release
    out = tmp_path / "v2report2.md"

    runner.invoke(
        app, ["report", str(model), "-l", "deep", "--analysis-json", str(v2), "--baseline", str(v1), "-o", str(out)]
    )

    assert out.exists()


def test_the_renamed_release_report_carries_a_baseline_section(
    runner: CliRunner, renamed_release: tuple[Path, Path, Path], tmp_path: Path
) -> None:
    """Accepting the flag and then dropping its content silently would be the same defect."""
    model, v1, v2 = renamed_release
    out = tmp_path / "v2report3.md"

    runner.invoke(
        app, ["report", str(model), "-l", "deep", "--analysis-json", str(v2), "--baseline", str(v1), "-o", str(out)]
    )

    assert "Baseline" in out.read_text(encoding="utf-8")


def test_a_baseline_from_the_previous_revision_of_a_grown_model_is_accepted(runner: CliRunner, tmp_path: Path) -> None:
    """Growth is the change a baseline exists to show; it must not read as a change of system."""
    model = _init(runner, _TEMPLATE_B, tmp_path / "grown.otm.yaml")
    v1 = _analyze(runner, model, tmp_path / "g1.analysis.json")
    _append_component(model)
    v2 = _analyze(runner, model, tmp_path / "g2.analysis.json")
    out = tmp_path / "grown.md"

    result = runner.invoke(
        app, ["report", str(model), "-l", "deep", "--analysis-json", str(v2), "--baseline", str(v1), "-o", str(out)]
    )

    assert result.exit_code == 0, _out(result)


def test_the_surfaces_now_agree_with_diff_analysis_on_the_renamed_pair(
    runner: CliRunner, renamed_release: tuple[Path, Path, Path]
) -> None:
    """The pair `report --baseline` refused was gated cleanly by the sibling command."""
    _, v1, v2 = renamed_release

    result = runner.invoke(app, ["diff-analysis", str(v1), str(v2), "--fail-on", "high"])

    assert result.exit_code == 0, _out(result)


# --- the title survives as the last evidence of an edit, for `--analysis-json` only ---------------


def test_renaming_the_model_still_invalidates_its_own_analysis(
    runner: CliRunner, renamed_release: tuple[Path, Path, Path]
) -> None:
    """`--analysis-json` claims to be *this* revision's analysis, and the model changed since.

    Nothing structural can see a rename, so with no fingerprint in the artifact the title is the
    only evidence left that the document was edited after the analysis ran. Dropping it would
    weaken the very staleness detection these tests exist to add, and `/v1/exports` and friends
    already refuse the same pair — the surfaces have to agree. The recovery is one command, and
    the message says which.
    """
    model, v1, _ = renamed_release

    result = runner.invoke(app, ["report", str(model), "-l", "deep", "--analysis-json", str(v1)])

    assert result.exit_code == _REFUSED, _out(result)


def test_the_rename_refusal_names_both_titles(runner: CliRunner, renamed_release: tuple[Path, Path, Path]) -> None:
    model, v1, _ = renamed_release

    result = runner.invoke(app, ["report", str(model), "-l", "deep", "--analysis-json", str(v1)])

    assert "Orders Platform (formerly async API)" in _out(result)
