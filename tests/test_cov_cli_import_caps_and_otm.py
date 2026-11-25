"""`otm import` on inputs bigger or emptier than the happy path.

Two untested behaviours, both of which only show up on real repositories:

* **the draft caps.** `scan_payload_to_draft_yaml` emits at most 24 service components and 48 data
  flows. The cap on components is applied *before* the flows are built, so a route file that lost
  its component must be skipped when the flows are generated — otherwise the draft would declare a
  flow pointing at a component that is not in the document, and `otm validate` (the very next step
  the CLI advertises for a draft) would reject the file the tool just produced. Nothing covered
  either cap, so nothing proved the two limits agreed with each other.

* **`import otm` with nothing to report.** The loss notice is well tested when there *is* loss; the
  silent path is what keeps stdout pipeable, and it had no test.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from click.testing import Result
from otm_cli.application.import_service import scan_payload_to_draft_yaml
from otm_cli.cli import app
from typer.testing import CliRunner

_DRAFT_MAX_COMPONENTS = 24
_DRAFT_MAX_FLOWS = 48


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _wide_console(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "300")


def _out(result: Result) -> str:
    return (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")


def _route(file_path: str, route: str) -> dict[str, str]:
    """One `route` inference, shaped exactly as `scan_node_express_repo` emits it."""
    return {
        "kind": "route",
        "message": f"Rota HTTP encontrada em `{file_path}`",
        "evidence": route,
        "confidence": "medium",
        "inference_source": "regex_heuristic",
    }


def _draft(payload: dict[str, Any]) -> dict[str, Any]:
    parsed: dict[str, Any] = yaml.safe_load(scan_payload_to_draft_yaml(payload))
    return parsed


def _service_ids(draft: dict[str, Any]) -> set[str]:
    return {c["id"] for c in draft["components"] if c["id"].startswith("svc_")}


def _validates(runner: CliRunner, tmp_path: Path, draft: dict[str, Any]) -> Result:
    target = tmp_path / "draft.otm.yaml"
    target.write_text(yaml.safe_dump(draft, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return runner.invoke(app, ["validate", str(target)])


# --------------------------------------------------------------------------- the component cap


def _oversized_repo_payload() -> dict[str, Any]:
    """30 route files — six more than the draft is allowed to turn into components."""
    return {
        "root": "/srv/big-service",
        "inferences": [_route(f"src/routes/r{n:02d}.js", f"/api/r{n:02d}") for n in range(30)],
    }


def test_component_cap_is_applied_to_the_draft() -> None:
    draft = _draft(_oversized_repo_payload())
    assert len(_service_ids(draft)) == _DRAFT_MAX_COMPONENTS


def test_routes_from_capped_away_files_do_not_become_dangling_flows() -> None:
    """The bug the cap has to avoid: a flow whose target component was never declared."""
    draft = _draft(_oversized_repo_payload())
    declared = {c["id"] for c in draft["components"]}
    targets = {f["to_component"] for f in draft["data_flows"]}
    assert targets <= declared
    assert len(draft["data_flows"]) == _DRAFT_MAX_COMPONENTS


def test_a_capped_draft_is_still_a_valid_model(runner: CliRunner, tmp_path: Path) -> None:
    """`import repo --draft-out` promises a draft that chains into `otm validate`."""
    result = _validates(runner, tmp_path, _draft(_oversized_repo_payload()))
    assert result.exit_code == 0, _out(result)


# --------------------------------------------------------------------------- the data-flow cap


def _oversized_route_payload() -> dict[str, Any]:
    """One file with more routes than the flow budget, plus a second file behind it."""
    inferences = [_route("src/routes/a.js", f"/api/a/{n}") for n in range(60)]
    inferences.append(_route("src/routes/b.js", "/api/b/0"))
    return {"root": "/srv/chatty-service", "inferences": inferences}


def test_data_flow_cap_stops_the_draft_growing() -> None:
    draft = _draft(_oversized_route_payload())
    assert len(draft["data_flows"]) == _DRAFT_MAX_FLOWS


def test_the_flow_cap_stops_every_remaining_file_not_just_the_current_one() -> None:
    """Once the budget is spent the whole loop ends — the second file contributes no flow."""
    draft = _draft(_oversized_route_payload())
    targets = {f["to_component"] for f in draft["data_flows"]}
    assert "svc_b" not in targets
    assert "svc_b" in _service_ids(draft), "the file is still a component; only its flows were cut"


def test_a_flow_capped_draft_is_still_a_valid_model(runner: CliRunner, tmp_path: Path) -> None:
    result = _validates(runner, tmp_path, _draft(_oversized_route_payload()))
    assert result.exit_code == 0, _out(result)


# --------------------------------------------------------------------------- `import otm`


def test_import_otm_on_a_missing_file_is_a_usage_error(runner: CliRunner, tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist.otm.json"
    result = runner.invoke(app, ["import", "otm", str(missing)])
    report = _out(result)
    assert result.exit_code == 1
    assert "not a file" in report
    assert "Traceback" not in report


def test_import_otm_keeps_stdout_pipeable_when_nothing_was_dropped(runner: CliRunner, tmp_path: Path) -> None:
    """No loss means no notice: stdout must be the canonical YAML and nothing else."""
    source = tmp_path / "clean.otm.json"
    source.write_text(
        json.dumps(
            {
                "otmVersion": "0.2.0",
                "project": {"id": "p", "name": "Clean"},
                "components": [{"id": "c-api", "name": "API", "type": "web-service"}],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(app, ["import", "otm", str(source)])
    assert result.exit_code == 0
    assert "Not imported" not in _out(result)

    emitted = yaml.safe_load(result.stdout)
    assert emitted["metadata"]["title"] == "Clean"
