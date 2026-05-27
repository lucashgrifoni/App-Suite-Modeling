"""
Coverage sweep — exercises the analyze→export→render→compare pipeline across every example
document, locale, and report level. Drives the many content/edge branches in exporters and
report-premium that single-fixture tests miss (no assertions on exact text — structural smoke).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_core_schema import load_document_from_yaml_path
from otm_exporters.analysis_markdown import export_analysis_markdown, export_document_and_analysis_markdown
from otm_exporters.comparison_markdown import export_comparison_markdown
from otm_threat_engine import analyze_document
from otm_threat_engine.threat_model_comparison import compare_threat_models

pytest.importorskip("fastapi")
from otm_report_premium.builder import build_premium_report_payload  # noqa: E402
from otm_report_premium.enums import ReportLevel  # noqa: E402
from otm_report_premium.render_html import render_premium_html  # noqa: E402
from otm_report_premium.render_markdown import render_premium_markdown  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]
_DOCS = sorted(str(p) for p in (_ROOT / "examples").rglob("*.otm.yaml"))
_LEVELS = [ReportLevel.EXECUTIVE, ReportLevel.STANDARD, ReportLevel.DEEP]


@pytest.mark.parametrize("doc_path", _DOCS)
def test_pipeline_sweep_per_document(doc_path: str) -> None:
    doc = load_document_from_yaml_path(doc_path)
    result = analyze_document(doc, auto_recommend=True)

    # Analysis markdown in both locales (drives recommendation/risk-category/framework-ref branches).
    for locale in (None, "en", "pt-BR"):
        assert export_analysis_markdown(result, locale=locale)
        assert export_document_and_analysis_markdown(doc, result, locale=locale)

    # Premium payload + both renderers at every depth (drives tier/section/guard branches).
    for level in _LEVELS:
        for locale in ("pt-BR", "en"):
            payload = build_premium_report_payload(doc, result, level=level, locale=locale)
            assert render_premium_markdown(payload)
            assert render_premium_html(payload)


def test_pipeline_sweep_comparisons() -> None:
    # Compare across heterogeneous domains to drive comparison/semantic-diff/insight branches.
    docs = [load_document_from_yaml_path(p) for p in _DOCS]
    analyses = [analyze_document(d, auto_recommend=True) for d in docs]
    for i in range(len(docs) - 1):
        cmp = compare_threat_models(
            docs[i],
            docs[i + 1],
            baseline_analysis=analyses[i],
            revised_analysis=analyses[i + 1],
        )
        assert export_comparison_markdown(cmp)
    # Self-compare (no changes) drives the "no diff" guard branches.
    same = compare_threat_models(docs[0], docs[0], baseline_analysis=analyses[0], revised_analysis=analyses[0])
    assert export_comparison_markdown(same)


def test_pipeline_premium_with_baseline() -> None:
    # Premium payload WITH a baseline drives the baseline/delta + semantic-diff render sections.
    docs = [load_document_from_yaml_path(p) for p in _DOCS]
    base = analyze_document(docs[0], auto_recommend=True)
    rev = analyze_document(docs[-1], auto_recommend=True)
    payload = build_premium_report_payload(docs[-1], rev, level=ReportLevel.DEEP, baseline=base)
    assert render_premium_markdown(payload)
    assert render_premium_html(payload)
