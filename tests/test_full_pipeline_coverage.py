"""Data-driven coverage — run the full pipeline over every example model.

Exercises engine internals (wizard signals, anti-patterns, composite heuristics,
risk calc/aggregate, methodology lenses, semantic comparison) plus exporters and
core-schema (diff, insights, fit matrix, quality precheck) across diverse real models
(including the PLOT4ai AI calibration set).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_core_schema import diff_documents, load_document_from_yaml_path
from otm_core_schema.diff_insights import structural_key_insights
from otm_core_schema.enums import ThreatModelMethodology
from otm_core_schema.methodology_fit_matrix import build_methodology_fit_matrix
from otm_core_schema.model_quality_precheck import assess_model_precheck
from otm_exporters import (
    export_analysis_markdown,
    export_comparison_markdown,
    export_document_markdown,
    export_flowchart_mermaid,
    export_remediation_backlog_markdown,
)
from otm_threat_engine import (
    analyze_document,
    build_remediation_backlog,
    compare_threat_models,
    recommend_methodology,
)

_ROOT = Path(__file__).resolve().parents[1]
_MODELS = sorted(str(p) for p in (_ROOT / "examples").rglob("*.otm.yaml"))
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_models_discovered() -> None:
    assert len(_MODELS) >= 12


@pytest.mark.parametrize("model", _MODELS)
def test_full_pipeline_per_model(model: str) -> None:
    doc = load_document_from_yaml_path(model)
    res = analyze_document(doc)
    assert res.document_title is not None

    # exporters
    assert export_analysis_markdown(res)
    assert export_analysis_markdown(res, locale="en")
    assert export_document_markdown(doc)
    assert export_flowchart_mermaid(doc).startswith("flowchart")

    # remediation backlog (+ markdown groupings)
    backlog = build_remediation_backlog(res, doc)
    for group_by in (None, "root-cause", "control", "category"):
        assert export_remediation_backlog_markdown(backlog, group_by=group_by)

    # core-schema quality / fit / recommendation
    assess_model_precheck(doc)
    build_methodology_fit_matrix(doc)
    recommend_methodology(doc)

    # diff vs minimal + structural insights + comparison markdown
    base = load_document_from_yaml_path(_MINIMAL)
    d = diff_documents(base, doc)
    structural_key_insights(base, doc, d)
    comp = compare_threat_models(base, doc, baseline_analysis=analyze_document(base), revised_analysis=res)
    assert export_comparison_markdown(comp)


@pytest.mark.parametrize("methodology", [m.value for m in ThreatModelMethodology])
def test_all_methodologies_on_rich_model(methodology: str) -> None:
    doc = load_document_from_yaml_path(_ROOT / "examples" / "saas-ordering-v1.otm.yaml")
    res = analyze_document(doc, methodology=methodology)
    assert res.methodology.value == methodology


@pytest.mark.parametrize("model", _MODELS)
def test_auto_recommend_per_model(model: str) -> None:
    doc = load_document_from_yaml_path(model)
    res = analyze_document(doc, auto_recommend=True)
    assert res.methodology is not None
