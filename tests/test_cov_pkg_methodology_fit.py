"""Methodology fit — the single-methodology entry point and the PLOT4ai middle rating.

`fit_for_methodology` is exported from `otm_core_schema` but nothing in the tree calls it;
everything goes through `build_methodology_fit_matrix`, which caches the context once. The two
must not drift, because a caller asking about one methodology has to get the same answer the
matrix would give.

`plot4ai` is the only methodology whose "partial" rating has a rule of its own: an AI system
that has not been modelled deeply enough (no assets, no trust boundaries) is still a candidate
for the AI lens, and rating it "weak" would hide the lens from exactly the models that need it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_core_schema import (
    Metadata,
    ModelInfo,
    ThreatModelDocument,
    ThreatModelMethodology,
    build_methodology_fit_matrix,
    fit_for_methodology,
    load_document_from_yaml_path,
)
from otm_core_schema.ai_context import looks_like_ai_context
from otm_core_schema.document import Component, DataFlow
from otm_core_schema.enums import ComponentKind

_EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _shallow_ai_document() -> ThreatModelDocument:
    """An AI system sketched out, with no assets and no trust boundaries yet."""
    return ThreatModelDocument(
        model_info=ModelInfo(),
        metadata=Metadata(title="LLM assistant", summary="Assistente com LLM e prompt de sistema"),
        components=[
            Component(id="user", name="User", kind=ComponentKind.USER),
            Component(id="llm", name="LLM inference", kind=ComponentKind.PROCESS, technology="OpenAI GPT"),
        ],
        data_flows=[DataFlow(id="ask", name="prompt", from_component="user", to_component="llm")],
    )


def test_a_shallow_ai_model_is_recognised_as_an_ai_system() -> None:
    """Premise of the rating below: the engine does see this as AI."""
    assert looks_like_ai_context(_shallow_ai_document()) is True


def test_a_shallow_ai_model_rates_plot4ai_partial_not_weak() -> None:
    doc = _shallow_ai_document()

    assert not doc.assets, "the point of the fixture is the missing assets"
    assert not doc.trust_boundaries, "the point of the fixture is the missing boundaries"
    assert build_methodology_fit_matrix(doc)["plot4ai"] == "partial"


def test_a_model_with_no_ai_signal_rates_plot4ai_weak() -> None:
    """Control: "partial" has to mean something, so a non-AI model must not reach it."""
    plain = load_document_from_yaml_path(_EXAMPLES / "minimal.otm.yaml")

    assert build_methodology_fit_matrix(plain)["plot4ai"] == "weak"


def test_the_matrix_rates_every_supported_methodology() -> None:
    """A methodology missing from the matrix would silently vanish from the pre-check."""
    doc = load_document_from_yaml_path(_EXAMPLES / "saas-ordering-v1.otm.yaml")

    assert set(build_methodology_fit_matrix(doc)) == {m.value for m in ThreatModelMethodology}


@pytest.mark.parametrize("methodology", list(ThreatModelMethodology))
def test_the_single_methodology_call_agrees_with_the_matrix(methodology: ThreatModelMethodology) -> None:
    doc = load_document_from_yaml_path(_EXAMPLES / "saas-ordering-v1.otm.yaml")
    matrix = build_methodology_fit_matrix(doc)

    assert fit_for_methodology(doc, methodology) == matrix[methodology.value]


def test_the_single_methodology_call_agrees_on_a_shallow_ai_model() -> None:
    """The interesting case: the matrix builds the AI context once, the single call rebuilds it."""
    doc = _shallow_ai_document()

    assert fit_for_methodology(doc, ThreatModelMethodology.PLOT4AI) == "partial"
