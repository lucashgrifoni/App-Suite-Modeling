"""Round-4: the one identity module every pairing guard reads, and the engine facts it rests on.

`otm report --analysis-json`, `otm report --baseline`, `otm backlog --document`, the API's
`document`+`analysis` routes and `otm diff-analysis` all ask "do these two artifacts belong
together?". Four of the five answered it by comparing `document_title`, and that signal fails in
both directions: `otm init -t <template>` copies the template's title verbatim (so two unrelated
models collide on it), and renaming a model between releases (so the same model stops matching
itself).

`otm_threat_engine.analysis_identity` replaces it. This file pins the two engine facts the module
depends on, because a change to either turns a correct guard into a wrong one silently:

1. every component of the analysed document yields at least one heuristic threat, which is what
   makes "a component the analysis never names" mean "added after the analysis ran";
2. no heuristic targets an entity the document does not define, which is what makes a foreign
   entity proof of a different document.

Fact 1 has exactly one exception — the `cia_die` lens returns a top-ten selection instead of an
enumeration — and `_SUMMARISING_METHODOLOGIES` exists for it. If another lens starts summarising,
`test_every_methodology_except_the_summarising_one_names_every_component` fails here rather than
turning into false refusals in front of a user.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from otm_core_schema import ThreatModelDocument, ThreatModelMethodology, load_document_from_yaml_path
from otm_industry_packs.loader import load_pack
from otm_threat_engine import AnalysisResult, analyze_document
from otm_threat_engine.analysis_identity import (
    MIN_SHARED_SHAPE,
    foreign_entity_ids,
    structural_shape,
    system_overlap,
    unanalysed_component_ids,
)

_ROOT = Path(__file__).resolve().parents[1]
_SAAS = _ROOT / "examples" / "saas-ordering-v1.otm.yaml"
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"

#: A schema-valid model with no components and no flows: no shape at all.
_STRUCTURELESS: dict[str, Any] = {
    "model": {"schema_version": "1.0.0", "system_type": "web_application"},
    "metadata": {"title": "Structureless stub", "owner": "appsec@empresa.example"},
}


def _saas() -> dict[str, Any]:
    return yaml.safe_load(_SAAS.read_text(encoding="utf-8"))


def _doc(payload: dict[str, Any]) -> ThreatModelDocument:
    return ThreatModelDocument.model_validate(payload)


@pytest.fixture
def saas_doc() -> ThreatModelDocument:
    return load_document_from_yaml_path(_SAAS)


@pytest.fixture
def saas_analysis(saas_doc: ThreatModelDocument) -> AnalysisResult:
    return analyze_document(saas_doc)


# --- fact 1: an analysis names every component of its own document -----------------------------


@pytest.mark.parametrize("methodology", [m for m in ThreatModelMethodology if m is not ThreatModelMethodology.CIA_DIE])
def test_every_methodology_except_the_summarising_one_names_every_component(
    saas_doc: ThreatModelDocument, methodology: ThreatModelMethodology
) -> None:
    analysis = analyze_document(saas_doc, methodology=methodology)

    assert unanalysed_component_ids(saas_doc, analysis) == []


def test_the_summarising_lens_really_does_drop_components(saas_doc: ThreatModelDocument) -> None:
    """Why `cia_die` is excluded, pinned so the exception cannot become dead weight.

    It keeps the ten highest-scoring active threats, so most components go unnamed in a
    perfectly fresh analysis. Reading that as staleness would refuse a correct pair.
    """
    analysis = analyze_document(saas_doc, methodology=ThreatModelMethodology.CIA_DIE)
    named = {t.target_component_id for t in analysis.heuristic_threats if t.target_component_id}

    assert named < {c.id for c in saas_doc.components}


def test_the_summarising_lens_is_exempt_from_the_staleness_signal(saas_doc: ThreatModelDocument) -> None:
    analysis = analyze_document(saas_doc, methodology=ThreatModelMethodology.CIA_DIE)

    assert unanalysed_component_ids(saas_doc, analysis) == []


@pytest.mark.parametrize("pack_id", ["cloud_native", "finance", "saas", "telecom", "transport"])
def test_a_pack_does_not_break_component_coverage(saas_doc: ThreatModelDocument, pack_id: str) -> None:
    """A pack adds and re-scores heuristics; it must not make a fresh analysis look stale."""
    analysis = analyze_document(saas_doc, pack=load_pack(pack_id))

    assert unanalysed_component_ids(saas_doc, analysis) == []


def test_a_suppressed_duplicate_still_counts_as_seeing_the_component(saas_doc: ThreatModelDocument) -> None:
    """Noise suppression flags `skipped_as_duplicate`; it must not hide the entity."""
    analysis = analyze_document(saas_doc)
    marked = analysis.model_copy(
        update={
            "heuristic_threats": [
                t.model_copy(update={"skipped_as_duplicate": True}) for t in analysis.heuristic_threats
            ]
        }
    )

    assert unanalysed_component_ids(saas_doc, marked) == []


# --- fact 2: an analysis never names an entity its document does not define --------------------


@pytest.mark.parametrize("methodology", list(ThreatModelMethodology))
def test_no_methodology_invents_an_entity(saas_doc: ThreatModelDocument, methodology: ThreatModelMethodology) -> None:
    analysis = analyze_document(saas_doc, methodology=methodology)

    assert foreign_entity_ids(saas_doc, analysis) == []


def test_a_deleted_component_shows_up_as_a_foreign_entity(saas_doc: ThreatModelDocument) -> None:
    """The mirror of staleness: the document lost an entity the analysis still hangs threats off."""
    analysis = analyze_document(saas_doc)
    shrunk = _saas()
    shrunk["components"] = [c for c in shrunk["components"] if c["id"] != "cache"]
    shrunk["data_flows"] = [f for f in shrunk["data_flows"] if "cache" not in (f["from_component"], f["to_component"])]
    for boundary in shrunk["trust_boundaries"]:
        members = boundary.get("member_component_ids")
        if members:
            boundary["member_component_ids"] = [c for c in members if c != "cache"]

    assert "component:cache" in foreign_entity_ids(_doc(shrunk), analysis)


def test_an_added_component_shows_up_as_unanalysed(
    saas_doc: ThreatModelDocument, saas_analysis: AnalysisResult
) -> None:
    grown = _saas()
    grown["components"].append({"id": "legacy_ftp", "name": "FTP legado", "kind": "external_entity"})

    assert unanalysed_component_ids(_doc(grown), saas_analysis) == ["legacy_ftp"]


def test_an_added_component_is_not_mistaken_for_a_foreign_entity(saas_analysis: AnalysisResult) -> None:
    """The two signals must stay distinct: growth is staleness, not a different system."""
    grown = _saas()
    grown["components"].append({"id": "legacy_ftp", "name": "FTP legado", "kind": "external_entity"})

    assert foreign_entity_ids(_doc(grown), saas_analysis) == []


# --- the same-system relation -------------------------------------------------------------------


def test_a_rename_leaves_the_structural_shape_untouched(saas_analysis: AnalysisResult) -> None:
    renamed = _saas()
    renamed["metadata"]["title"] = "Orders Platform (formerly async API)"

    assert structural_shape(analyze_document(_doc(renamed))) == structural_shape(saas_analysis)


def test_a_renamed_revision_is_the_same_system(saas_analysis: AnalysisResult) -> None:
    renamed = _saas()
    renamed["metadata"]["title"] = "Orders Platform (formerly async API)"

    assert system_overlap(saas_analysis, analyze_document(_doc(renamed))).is_same_system


def test_a_grown_revision_is_the_same_system(saas_analysis: AnalysisResult) -> None:
    grown = _saas()
    for i in range(12):
        grown["components"].append({"id": f"svc{i}", "name": f"Serviço {i}", "kind": "process"})

    assert system_overlap(saas_analysis, analyze_document(_doc(grown))).is_same_system


def test_two_unrelated_models_are_not_the_same_system(saas_analysis: AnalysisResult) -> None:
    other = analyze_document(load_document_from_yaml_path(_MINIMAL))

    assert not system_overlap(saas_analysis, other).is_same_system


def test_two_unrelated_models_sharing_a_title_are_still_not_the_same_system(saas_analysis: AnalysisResult) -> None:
    """The defect: identity by title, and every model from one template carries the same title."""
    other = analyze_document(load_document_from_yaml_path(_MINIMAL))
    disguised = other.model_copy(update={"document_title": saas_analysis.document_title})

    assert not system_overlap(saas_analysis, disguised).is_same_system


def test_a_shapeless_analysis_is_never_declared_a_different_system(saas_analysis: AnalysisResult) -> None:
    """No evidence is not evidence of mismatch — refusing here would mask a real result."""
    stub = analyze_document(_doc(_STRUCTURELESS))

    assert system_overlap(stub, saas_analysis).is_same_system


def test_the_quorum_sits_between_the_measured_populations() -> None:
    """The threshold is a measurement, not a preference; pin it so a tweak is deliberate."""
    assert MIN_SHARED_SHAPE == pytest.approx(2 / 3)
