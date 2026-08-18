"""P3 security regression — a content-free `threats:` entry must not disarm the drift gate.

`existing_threat_keys` decided that the document already covered a heuristic from
`(target_component_id, target_data_flow_id, stride)` alone. `Threat.risk` is optional, so four
lines — id, title `"n/a"`, stride, target — were a schema-valid declaration that marked the
matching engine heuristics `skipped_as_duplicate`.

That mark is a hard exclusion filter in `analysis_diff`, so the heuristics were removed *before*
the diff was built: the gate never saw them, `unranked_threat_ids` never reported them (it only
covers threats present in the diff), and the verdict flipped from "3 new threats at/above high,
exit 3" to "No new or worsened threats at or above the threshold", exit 0. The reviewer saw
`[threats] +3` in the diff body, which reads as threat-modelling work rather than as the gate
being switched off.

This is the same shape as the `methodology:` fail-open the project already closed: one line
inside the artifact under review disarming the control that reviews it. The file is written by
the PR author either way, so the fix is not to trust it — it is to make a declaration cost
something. `RiskAssessment` requires `likelihood` and `impact`, so claiming coverage now means
writing a number the reviewer can see and argue with.

The second half pins the direction that matters just as much: a real, scored declaration must
still suppress, or the fix would have turned every properly modelled threat into gate noise.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

import pytest
import yaml
from otm_cli.cli import app
from otm_core_schema import (
    RiskAssessment,
    StrideCategory,
    Threat,
    ThreatModelDocument,
    load_document_from_yaml_path,
)
from otm_threat_engine import analyze_document
from otm_threat_engine.engine_support import existing_threat_keys
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]
_SAAS = _ROOT / "examples" / "saas-ordering-v1.otm.yaml"
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"
_GATE_TRIP = 3

_STUB_STRIDES = ("tampering", "information_disclosure", "denial_of_service")


def _stub_threats(target: str) -> list[dict[str, Any]]:
    """Exactly what an author would type to make a red gate green, and nothing more."""
    return [
        {"id": f"noted_{i}", "title": "n/a", "stride": stride, "target_component_id": target}
        for i, stride in enumerate(_STUB_STRIDES, start=1)
    ]


def _scored_threats(target: str) -> list[dict[str, Any]]:
    """The same coverage claim, but carrying the risk assessment the schema allows."""
    return [
        {
            "id": f"noted_{i}",
            "title": "Reviewed export path",
            "stride": stride,
            "target_component_id": target,
            "risk": {"likelihood": 3, "impact": 4},
        }
        for i, stride in enumerate(_STUB_STRIDES, start=1)
    ]


@pytest.fixture
def gate_models(tmp_path: Path) -> tuple[Path, Path]:
    """Base, and a head that adds one sensitive datastore — three new HIGH heuristics."""
    base_payload = yaml.safe_load(_SAAS.read_text(encoding="utf-8"))
    head_payload = copy.deepcopy(base_payload)
    head_payload["components"].append(
        {"id": "pii_export_store", "name": "PII export store", "kind": "datastore", "handles_sensitive_data": True}
    )
    base = tmp_path / "base.otm.yaml"
    head = tmp_path / "head.otm.yaml"
    base.write_text(yaml.safe_dump(base_payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    head.write_text(yaml.safe_dump(head_payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return base, head


def _head_with(gate_models: tuple[Path, Path], declared: list[dict[str, Any]]) -> Path:
    base, head = gate_models
    payload = yaml.safe_load(head.read_text(encoding="utf-8"))
    payload["threats"] = [*declared, *payload.get("threats", [])]
    muted = head.parent / "head_declared.otm.yaml"
    muted.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    assert base.exists()
    return muted


# ------------------------------------------------------- the bypass is closed


def test_a_stub_declaration_does_not_cover_a_heuristic() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    stubbed = doc.model_copy(
        update={
            "threats": [Threat(id="noted_1", title="n/a", stride=StrideCategory.SPOOFING, target_component_id="user")]
        }
    )

    assert existing_threat_keys(stubbed) == set()


def test_a_stub_declaration_leaves_the_engine_heuristic_active() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    stubbed = doc.model_copy(
        update={
            "threats": [Threat(id="noted_1", title="n/a", stride=StrideCategory.SPOOFING, target_component_id="user")]
        }
    )

    by_id = {h.id: h for h in analyze_document(stubbed).heuristic_threats}

    assert by_id["eng_user_spoofing"].skipped_as_duplicate is False


def test_stub_declarations_cannot_silence_the_armed_gate(gate_models: tuple[Path, Path]) -> None:
    base, _head = gate_models
    muted = _head_with(gate_models, _stub_threats("pii_export_store"))

    run = CliRunner().invoke(
        app, ["diff", str(base), str(muted), "--with-analysis", "-m", "stride", "--fail-on", "high"]
    )

    assert run.exit_code == _GATE_TRIP, run.output


def test_the_gate_still_names_the_threats_the_stubs_tried_to_hide(gate_models: tuple[Path, Path]) -> None:
    base, _head = gate_models
    muted = _head_with(gate_models, _stub_threats("pii_export_store"))

    run = CliRunner().invoke(
        app, ["diff", str(base), str(muted), "--with-analysis", "-m", "stride", "--fail-on", "high"]
    )

    assert "eng_pii_export_store_information_disclosure" in run.output.replace("\n", "")


# --------------------------------- and a real declaration still does its job


def test_a_scored_declaration_still_covers_the_heuristic() -> None:
    """The opposite defect: modelled-and-scored threats must not become gate noise."""
    doc = load_document_from_yaml_path(_MINIMAL)
    declared = doc.model_copy(
        update={
            "threats": [
                Threat(
                    id="noted_1",
                    title="Reviewed",
                    stride=StrideCategory.SPOOFING,
                    target_component_id="user",
                    risk=RiskAssessment(likelihood=3, impact=3),
                )
            ]
        }
    )

    by_id = {h.id: h for h in analyze_document(declared).heuristic_threats}

    assert by_id["eng_user_spoofing"].skipped_as_duplicate is True


def test_a_scored_declaration_still_keeps_the_gate_quiet(gate_models: tuple[Path, Path]) -> None:
    base, _head = gate_models
    declared = _head_with(gate_models, _scored_threats("pii_export_store"))

    run = CliRunner().invoke(
        app, ["diff", str(base), str(declared), "--with-analysis", "-m", "stride", "--fail-on", "high"]
    )

    assert run.exit_code == 0, run.output


def test_the_shipped_examples_are_unaffected() -> None:
    """No model in the repository declares an unscored threat, so nothing regressed for users."""
    skip = (".venv", "build", ".claude", "node_modules")
    models = [p for p in _ROOT.rglob("*.otm.yaml") if not any(part in skip for part in p.parts)]
    assert models

    unscored = {
        str(path.relative_to(_ROOT)): [t.id for t in doc.threats if t.risk is None]
        for path, doc in ((p, _load(p)) for p in models)
        if doc is not None and any(t.risk is None for t in doc.threats)
    }

    assert unscored == {}


def _load(path: Path) -> ThreatModelDocument | None:
    try:
        return load_document_from_yaml_path(path)
    except Exception:  # pragma: no cover - fixtures that are intentionally invalid
        return None
