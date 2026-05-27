"""Coverage — API service branches (exports format dispatch, comparison analysis sources)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from otm_api.domain.export_formats import ExportFormat  # noqa: E402
from otm_api.services.compare import comparison_from_validated_documents  # noqa: E402
from otm_api.services.exports import _require_analysis, build_exports  # noqa: E402
from otm_core_schema import create_blank_document  # noqa: E402
from otm_threat_engine import analyze_document  # noqa: E402


def test_require_analysis_raises_when_missing() -> None:
    with pytest.raises(RuntimeError):
        _require_analysis(None)


def test_build_exports_document_and_analysis_formats() -> None:
    doc = create_blank_document()
    out = build_exports(
        doc,
        formats=[ExportFormat.document_json, ExportFormat.analysis_json, ExportFormat.analysis_markdown],
    )
    assert "document_json" in out  # document_json dispatch branch
    assert "analysis_json" in out  # analysis required -> run_analysis -> _require_analysis branch
    assert "analysis_markdown" in out


def test_comparison_with_explicit_analyses() -> None:
    doc = create_blank_document()
    analysis_dict = analyze_document(doc).model_dump(mode="json")
    cmp = comparison_from_validated_documents(
        doc,
        doc,
        baseline_analysis=analysis_dict,
        revised_analysis=analysis_dict,
    )
    assert cmp is not None  # explicit-analyses branch (model_validate)


def test_comparison_with_run_analysis_flag() -> None:
    doc = create_blank_document()
    cmp = comparison_from_validated_documents(doc, doc, run_analysis_flag=True)
    assert cmp is not None  # run_analysis_flag branch


def test_compare_body_requires_both_or_neither_analyses() -> None:
    import pydantic
    from otm_api.schemas.bodies import CompareBody

    # exactly one analysis provided -> the pair-validator raises (wrapped as ValidationError)
    with pytest.raises(pydantic.ValidationError):
        CompareBody(baseline={}, revised={}, baseline_analysis={"score_0_100": 1})
