"""Open Threat Model (OTM) interoperability bridge (P1 evolution step).

Import an IriusRisk OTM (0.2.0) document into the canonical schema and export the
canonical schema back to OTM, with id sanitisation, referential-integrity guards,
and a faithful structural round-trip.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from otm_artifact_import.otm_native import document_to_otm, import_otm_text, otm_to_document
from otm_cli.cli import app
from otm_core_schema import load_document_from_yaml_path
from typer.testing import CliRunner

_MINIMAL = Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml"


def test_export_produces_required_otm_fields() -> None:
    otm = document_to_otm(load_document_from_yaml_path(_MINIMAL))
    assert otm["otmVersion"] == "0.2.0"
    assert otm["project"]["id"] and otm["project"]["name"]
    assert otm["components"]
    for c in otm["components"]:
        assert c["id"] and c["name"] and c["type"]
    for z in otm.get("trustZones", []):
        assert z["risk"]["trustRating"]
    for a in otm.get("assets", []):
        assert {"confidentiality", "integrity", "availability"} <= set(a["risk"])
    for df in otm.get("dataflows", []):
        assert df["source"] and df["destination"]


def test_round_trip_preserves_structure() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    back = otm_to_document(document_to_otm(doc))
    assert sorted(c.id for c in back.components) == sorted(c.id for c in doc.components)
    assert sorted(c.kind.value for c in back.components) == sorted(c.kind.value for c in doc.components)
    assert len(back.trust_boundaries) == len(doc.trust_boundaries)
    assert {(f.from_component, f.to_component) for f in back.data_flows} == {
        (f.from_component, f.to_component) for f in doc.data_flows
    }


def test_import_otm_sanitizes_ids_maps_kinds_and_keeps_integrity() -> None:
    otm = {
        "otmVersion": "0.2.0",
        "project": {"id": "Proj 1", "name": "Demo"},
        "trustZones": [{"id": "Public Zone", "name": "Public", "risk": {"trustRating": 10}}],
        "components": [
            {"id": "Web App", "name": "Web", "type": "web-application", "parent": {"trustZone": "Public Zone"}},
            {"id": "DB!", "name": "Database", "type": "postgres-database", "parent": {"trustZone": "Public Zone"}},
        ],
        "dataflows": [{"id": "flow A", "name": "query", "source": "Web App", "destination": "DB!"}],
        "assets": [{"id": "PII Data", "name": "PII", "risk": {"confidentiality": 100}}],
    }
    # otm_to_document returns a *validated* ThreatModelDocument, so every id already
    # matches the canonical ENTITY_ID_PATTERN and every reference resolves.
    doc = otm_to_document(otm)
    ids = {c.id for c in doc.components}
    assert len(ids) == 2
    db = next(c for c in doc.components if c.name == "Database")
    assert db.kind.value == "datastore"  # postgres-database -> datastore
    web = next(c for c in doc.components if c.name == "Web")
    assert web.in_trust_boundary in {b.id for b in doc.trust_boundaries}
    flow = doc.data_flows[0]
    assert flow.from_component in ids and flow.to_component in ids


def test_import_otm_drops_dataflow_with_unknown_endpoint() -> None:
    otm = {
        "otmVersion": "0.2.0",
        "project": {"id": "p", "name": "P"},
        "components": [{"id": "a", "name": "A", "type": "process"}],
        "dataflows": [{"id": "f", "name": "x", "source": "a", "destination": "ghost"}],
    }
    doc = otm_to_document(otm)
    assert doc.data_flows == []  # dangling destination dropped, integrity preserved


def test_import_otm_text_rejects_non_mapping() -> None:
    import pytest

    with pytest.raises(ValueError):
        import_otm_text("- just\n- a\n- list\n")


def test_otm_collection_key_must_be_an_array_not_a_scalar() -> None:
    """Regression: a truthy non-list collection value used to raise an uncaught TypeError.

    `for x in otm.get(key) or []` only substituted falsy values, so `components: 5` reached
    the loop and crashed. A str/dict silently iterated characters/keys instead. Both now
    raise a ValueError the CLI renders as a friendly error, rather than importing an empty
    model (silent data loss) or printing a stack trace.
    """
    import pytest

    for key in ("trustZones", "components", "dataflows", "assets"):
        for bad in (5, 1.5, True, "abc", {"a": 1}):
            with pytest.raises(ValueError, match=f"`{key}` must be an array"):
                otm_to_document({"project": {"id": "p", "name": "P"}, key: bad})

    # Absent / null / empty stay valid and mean "no entries".
    for value in (None, []):
        doc = otm_to_document({"project": {"id": "p", "name": "P"}, "components": value})
        assert doc.components == []


def test_cli_import_otm_malformed_collection_is_a_friendly_error(tmp_path: Path) -> None:
    """The CLI must surface a CliUserError (exit 1), never an unhandled TypeError traceback."""
    bad = tmp_path / "hostile.otm.yaml"
    bad.write_text('otmVersion: "0.2.0"\nproject:\n  id: p\n  name: Demo\ndataflows: 3\n', encoding="utf-8")

    r = CliRunner().invoke(app, ["import", "otm", str(bad), "-o", str(tmp_path / "out.yaml")])
    assert r.exit_code == 1
    combined = (r.stdout or "") + (r.stderr or "")
    assert "must be an array" in combined
    assert "Traceback" not in combined and "TypeError" not in combined


def test_cli_export_otm_then_import_round_trip(tmp_path: Path) -> None:
    runner = CliRunner()
    otm_file = tmp_path / "model.otm.json"
    r1 = runner.invoke(app, ["export", str(_MINIMAL), "--format", "otm", "-o", str(otm_file)])
    assert r1.exit_code == 0, r1.output
    assert yaml.safe_load(otm_file.read_text(encoding="utf-8"))["otmVersion"] == "0.2.0"

    back_file = tmp_path / "back.otm.yaml"
    r2 = runner.invoke(app, ["import", "otm", str(otm_file), "-o", str(back_file)])
    assert r2.exit_code == 0, r2.output
    back = load_document_from_yaml_path(back_file)
    assert len(back.components) == len(load_document_from_yaml_path(_MINIMAL).components)
