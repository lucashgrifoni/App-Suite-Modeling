"""`otm import otm` must not advertise a conversion it does not perform.

The group help said the OTM conversion was "lossless" while the bridge itself documents the
opposite: it carries the architecture (project, trust zones, components, dataflows, assets) and
leaves OTM `threats`/`mitigations` behind. An analyst migrating out of IriusRisk/StartLeft saw
exit 0, no warning, and a canonical model with every hand-authored threat silently gone.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from otm_cli.application.import_service import import_otm
from otm_cli.cli import app
from typer.testing import CliRunner

_OTM_WITH_ANALYST_CONTENT = {
    "otmVersion": "0.2.0",
    "project": {"id": "iris", "name": "Iris payments"},
    "trustZones": [{"id": "tz-public", "name": "Public", "risk": {"trustRating": 10}}],
    "components": [
        {"id": "c-api", "name": "API", "type": "web-service", "parent": {"trustZone": "tz-public"}},
        {"id": "c-db", "name": "Cards DB", "type": "database", "parent": {"trustZone": "tz-public"}},
    ],
    "dataflows": [
        {"id": "df-1", "name": "query", "source": "c-api", "destination": "c-db"},
        {"id": "df-orphan", "name": "ghost", "source": "c-api", "destination": "c-missing"},
    ],
    "assets": [{"id": "a-pan", "name": "PAN", "risk": {"confidentiality": 100}}],
    "threats": [
        {
            "id": "t-sqli",
            "name": "SQL injection on Cards DB",
            "categories": ["Tampering"],
            "risk": {"likelihood": 80, "impact": 100},
        }
    ],
    "mitigations": [{"id": "m-param", "name": "Parameterised queries", "riskReduction": 90}],
}


@pytest.fixture()
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture(autouse=True)
def _wide_console(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("COLUMNS", "300")


def _src(tmp_path: Path) -> Path:
    p = tmp_path / "iris_src.otm.json"
    p.write_text(json.dumps(_OTM_WITH_ANALYST_CONTENT), encoding="utf-8")
    return p


def _out(result: object) -> str:
    return (getattr(result, "stdout", "") or "") + (getattr(result, "stderr", "") or "")


def test_import_help_does_not_claim_lossless(runner: CliRunner) -> None:
    r = runner.invoke(app, ["import", "--help"])
    assert r.exit_code == 0
    assert "lossless" not in _out(r).lower()


def test_import_otm_reports_what_it_dropped(runner: CliRunner, tmp_path: Path) -> None:
    """The emitted YAML always contains `threats: []`, so the notice must be its own text."""
    r = runner.invoke(app, ["import", "otm", str(_src(tmp_path))])
    out = _out(r).lower()
    assert r.exit_code == 0
    assert "not imported" in out, "the conversion loss was silent"
    assert "1 threat" in out and "1 mitigation" in out


def test_import_otm_notes_name_every_dropped_category(tmp_path: Path) -> None:
    _yaml_text, notes = import_otm(_src(tmp_path))
    joined = " ".join(notes).lower()
    assert "1 threat" in joined
    assert "1 mitigation" in joined
    assert "data flow" in joined, "the dataflow with an unknown endpoint was dropped silently"
    assert "risk" in joined, "OTM 0-100 risk attributes have no canonical equivalent"


def test_import_otm_still_returns_the_canonical_yaml(tmp_path: Path) -> None:
    """The conversion contract itself is unchanged — only the reporting is new."""
    yaml_text, _notes = import_otm(_src(tmp_path))
    doc = yaml.safe_load(yaml_text)
    assert doc["metadata"]["title"] == "Iris payments"
    assert len(doc["components"]) == 2


def test_import_otm_says_nothing_when_nothing_was_dropped(tmp_path: Path) -> None:
    clean = {
        "otmVersion": "0.2.0",
        "project": {"id": "p", "name": "Clean"},
        "components": [{"id": "c-api", "name": "API", "type": "web-service"}],
    }
    p = tmp_path / "clean.otm.json"
    p.write_text(json.dumps(clean), encoding="utf-8")
    _yaml_text, notes = import_otm(p)
    assert notes == []
