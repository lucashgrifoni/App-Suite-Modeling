"""Round-3 regression: `otm analyze --sarif-out` must point at the model it analysed.

The exporter learned to take a `model_uri` and anchor every result on it, but the CLI never
passed one — so every SARIF file the CLI produced claimed its findings lived in the exporter's
fallback name, `threat-model.otm.yaml`. Uploaded to GitHub code scanning that resolves to a path
that usually does not exist in the repository, and when several models are analysed in one run
their alerts all collapse onto the same phantom file.

Verified from the outside, the way CI uses it: run the command, read the artifact it wrote.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import pytest
from otm_cli.cli import app
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL_REL = "examples/minimal.otm.yaml"
_SAAS_REL = "examples/saas-ordering-v1.otm.yaml"

#: What the exporter falls back to when nobody names the file — correct for the API, wrong here.
_FALLBACK_URI = "threat-model.otm.yaml"


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


def _artifact_uris(sarif: Path) -> set[str]:
    payload: dict[str, Any] = json.loads(sarif.read_text(encoding="utf-8"))
    return {
        location["physicalLocation"]["artifactLocation"]["uri"]
        for result in payload["runs"][0]["results"]
        for location in result["locations"]
    }


def _analyze_to_sarif(runner: CliRunner, model: str, sarif: Path) -> set[str]:
    """Run the command and read back what it wrote; a failed run leaves no file and raises here."""
    runner.invoke(app, ["analyze", model, "--sarif-out", str(sarif), "--quiet"], catch_exceptions=False)
    return _artifact_uris(sarif)


def test_the_sarif_results_point_at_the_model_that_was_analysed(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(_ROOT)

    uris = _analyze_to_sarif(runner, _MINIMAL_REL, tmp_path / "minimal.sarif")

    assert uris == {_MINIMAL_REL}


def test_no_sarif_result_still_claims_the_fallback_model_name(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The exact bug: every result pointed at `threat-model.otm.yaml` whatever was analysed."""
    monkeypatch.chdir(_ROOT)

    uris = _analyze_to_sarif(runner, _MINIMAL_REL, tmp_path / "minimal.sarif")

    assert _FALLBACK_URI not in uris


def test_a_second_model_gets_its_own_uri(runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Two models analysed in one CI run must not collapse onto one file in code scanning."""
    monkeypatch.chdir(_ROOT)

    uris = _analyze_to_sarif(runner, _SAAS_REL, tmp_path / "saas.sarif")

    assert uris == {_SAAS_REL}


def test_a_nested_model_path_is_emitted_as_a_uri_not_a_windows_path(
    runner: CliRunner, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """`artifactLocation.uri` is a URI: GitHub cannot resolve `threat-models\\orders.otm.yaml`."""
    nested = tmp_path / "threat-models"
    nested.mkdir()
    shutil.copy(_ROOT / _MINIMAL_REL, nested / "orders.otm.yaml")
    monkeypatch.chdir(tmp_path)

    uris = _analyze_to_sarif(runner, "threat-models/orders.otm.yaml", tmp_path / "nested.sarif")

    assert uris == {"threat-models/orders.otm.yaml"}
