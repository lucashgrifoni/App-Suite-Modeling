"""Testes do pacote `otm_report_premium` — payload, priorização e renderização."""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_core_schema import load_document_from_yaml_path
from otm_report_premium import (
    build_premium_report_payload,
    html_to_pdf_bytes,
    render_premium_html,
    render_premium_markdown,
)
from otm_report_premium.enums import ReportLevel
from otm_threat_engine import analyze_document

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


@pytest.fixture()
def doc_and_result():
    doc = load_document_from_yaml_path(_MINIMAL)
    return doc, analyze_document(doc)


def test_build_payload_contains_top_risks_and_root_causes(doc_and_result) -> None:
    doc, result = doc_and_result
    payload = build_premium_report_payload(doc, result, level=ReportLevel.STANDARD)
    assert payload.executive_summary.threat_count >= 0
    assert isinstance(payload.top_risks, list)
    assert payload.cover.title == doc.metadata.title
    assert isinstance(payload.root_cause_groups, list)


def test_prioritization_tiers_present(doc_and_result) -> None:
    doc, result = doc_and_result
    payload = build_premium_report_payload(doc, result, level=ReportLevel.STANDARD)
    for tr in payload.top_risks:
        assert tr.priority_tier in ("P1", "P2", "P3")


def test_baseline_diff_none_without_baseline(doc_and_result) -> None:
    doc, result = doc_and_result
    payload = build_premium_report_payload(doc, result, level=ReportLevel.STANDARD)
    assert payload.baseline_diff is None


def test_markdown_renders_executive(doc_and_result) -> None:
    doc, result = doc_and_result
    payload = build_premium_report_payload(doc, result, level=ReportLevel.EXECUTIVE)
    md = render_premium_markdown(payload)
    assert "# " in md
    assert "Executive summary" in md


def test_pdf_bytes_from_html(doc_and_result) -> None:
    doc, result = doc_and_result
    payload = build_premium_report_payload(doc, result, level=ReportLevel.EXECUTIVE)
    html = render_premium_html(payload)
    pdf = html_to_pdf_bytes(html)
    assert pdf.startswith(b"%PDF")


def test_deep_has_appendix_or_voice(doc_and_result) -> None:
    doc, result = doc_and_result
    payload = build_premium_report_payload(doc, result, level=ReportLevel.DEEP)
    assert payload.technical_appendix is not None
    assert payload.methodology_voice
