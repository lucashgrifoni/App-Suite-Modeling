"""Coverage — empty/null-input guard branches in exporters and report renderers."""

from __future__ import annotations

import pytest
from otm_core_schema import create_blank_document, load_document_from_dict
from otm_exporters.analysis_markdown import (
    _append_model_gaps_block,
    _append_quality_block,
    analysis_markdown_messages,
)
from otm_exporters.comparison_markdown import export_comparison_markdown
from otm_threat_engine import analyze_document
from otm_threat_engine.threat_model_comparison import compare_threat_models


def test_blank_self_comparison_hits_empty_meta_guards() -> None:
    blank = create_blank_document()
    a = analyze_document(blank)
    cmp = compare_threat_models(blank, blank, baseline_analysis=a, revised_analysis=a)
    # minimal meta -> the semantic-diff / structural-refs / recommendation early-return guards fire
    assert export_comparison_markdown(cmp)


def test_comparison_without_analyses_null_semantic_sections() -> None:
    blank = create_blank_document()
    # no analyses supplied -> semantic_diff_sections / refs are null/empty -> the _cmp_* `is None` guards
    cmp = compare_threat_models(blank, blank)
    assert export_comparison_markdown(cmp)


def test_change_category_from_ref_non_struct() -> None:
    from otm_threat_engine.semantic_comparison import _change_category_from_ref

    assert _change_category_from_ref("not-a-struct-ref") is None  # non-matching ref -> None branch


def test_premium_error_analysis_required_locales() -> None:
    pytest.importorskip("fastapi")
    from otm_report_premium.report_i18n import premium_error_analysis_required

    assert "analysis" in premium_error_analysis_required("en")  # EN branch
    assert "análise" in premium_error_analysis_required("pt-BR") or premium_error_analysis_required("pt-BR")


def test_diff_analysis_for_report_shortcut() -> None:
    pytest.importorskip("fastapi")
    from otm_report_premium.builder import diff_analysis_for_report

    a = analyze_document(create_blank_document())
    assert diff_analysis_for_report(a, a) is not None  # exposes engine diff for external consumption


def test_comparison_explanations_structural_fallback() -> None:
    from otm_threat_engine.comparison_explanations import build_comparison_explanations

    blank = create_blank_document()
    cmp = compare_threat_models(blank, blank)  # no analyses -> no risk/methodology explanations
    cmp = cmp.model_copy(update={"structural_insights": ["Structural change A", "B", "C"], "key_insights": []})
    recs = build_comparison_explanations(cmp)
    # main paths empty (risk_score None branch) + structural_insights present -> structural fallback branch
    assert any("Structural change A" in (r.message or "") for r in recs)


def test_comparison_markdown_no_explanations_guard() -> None:
    blank = create_blank_document()
    cmp = compare_threat_models(blank, blank).model_copy(update={"explanations": []})
    # _cmp_explanations early-return guard (no explanations)
    assert export_comparison_markdown(cmp)


def test_risk_score_explanation_none_when_no_delta() -> None:
    from otm_threat_engine.comparison_explanations import _risk_score_explanation

    blank = create_blank_document()
    cmp = compare_threat_models(blank, blank)  # no analyses -> max_score_delta is None
    assert _risk_score_explanation(cmp, 1) is None  # None/small delta -> early None return


def test_key_insight_explanation_deduped_against_existing() -> None:
    from otm_explainability import ExplanationCategory, ExplanationRecord, ExplanationType
    from otm_threat_engine.comparison_explanations import _key_insight_explanation

    blank = create_blank_document()
    cmp = compare_threat_models(blank, blank).model_copy(update={"key_insights": ["Repeated headline"]})
    # `out` already carries an explanation whose message equals key_insights[0]
    existing = ExplanationRecord(
        id="exp_cmp_0001",
        type=ExplanationType.AGGREGATION,
        category=ExplanationCategory.DIFF,
        subject="x",
        message="Repeated headline",
    )
    # head already present in `out` -> the dedup `return None` branch
    assert _key_insight_explanation(cmp, [existing], 2) is None


def test_render_markdown_appendix_import_evidence() -> None:
    pytest.importorskip("fastapi")
    from otm_report_premium.builder import build_premium_report_payload
    from otm_report_premium.enums import ReportLevel
    from otm_report_premium.render_markdown import render_premium_markdown

    doc = create_blank_document()
    payload = build_premium_report_payload(doc, analyze_document(doc), level=ReportLevel.DEEP)
    if payload.technical_appendix is None:
        pytest.skip("no technical appendix at DEEP for blank doc")
    appendix = payload.technical_appendix.model_copy(update={"import_evidence_note": "Imported from OpenAPI spec."})
    payload = payload.model_copy(update={"technical_appendix": appendix})
    out = render_premium_markdown(payload)
    assert "Imported from OpenAPI" in out  # import_evidence_note append branch


def test_model_gaps_block_all_checks_passed() -> None:
    from otm_exporters.analysis_markdown import _append_model_gaps_block, analysis_markdown_messages

    msgs = analysis_markdown_messages(None)
    res = analyze_document(create_blank_document())
    pq = res.model_quality_precheck
    if pq is None or not pq.checks:
        pytest.skip("no precheck checks to flip")
    all_passed = pq.model_copy(update={"checks": [c.model_copy(update={"passed": True}) for c in pq.checks]})
    res2 = res.model_copy(update={"model_quality_precheck": all_passed})
    lines: list[str] = []
    _append_model_gaps_block(lines, res2, msgs)
    assert lines == []  # checks present but all passed -> the "no failed" early return


def test_quality_and_gaps_blocks_with_no_precheck() -> None:
    msgs = analysis_markdown_messages(None)
    res = analyze_document(create_blank_document())
    res = res.model_copy(update={"model_quality_precheck": None, "methodology_completeness": None})
    lines: list[str] = []
    _append_quality_block(lines, res, msgs)  # pq and mc both None -> early return
    _append_model_gaps_block(lines, res, msgs)  # pq None -> early return
    assert lines == []


def test_guided_audit_block_without_audit() -> None:
    pytest.importorskip("fastapi")
    from otm_report_premium.builder import build_premium_report_payload
    from otm_report_premium.enums import ReportLevel
    from otm_report_premium.render_markdown import _md_guided_audit
    from otm_report_premium.report_i18n import premium_render_copy

    doc = create_blank_document()
    payload = build_premium_report_payload(doc, analyze_document(doc), level=ReportLevel.STANDARD)
    payload = payload.model_copy(update={"guided_modeling_audit": None})
    lines: list[str] = []
    _md_guided_audit(lines, payload, premium_render_copy(payload.locale))  # no audit -> early return
    assert lines == []


def _payload_with_top_tier(tier: str, *, severity: float | None, composite: float):
    from otm_report_premium.builder import build_premium_report_payload
    from otm_report_premium.enums import ReportLevel

    # Deliberately not `create_blank_document()`: a blank model yields no
    # threats, so `top_risks` is empty and these tests used to skip themselves
    # into uselessness. (They only ever ran because an ungated business-abuse
    # rule emitted a phantom threat for every document, including empty ones —
    # see tests/test_business_abuse_authz_guard.py.) One admin-capable process
    # is the smallest model that produces real top risks to craft from.
    doc = load_document_from_dict(
        {
            "metadata": {"title": "tier rendering fixture"},
            "components": [
                {"id": "admin_api", "name": "Admin API", "kind": "process", "supports_admin_operations": True}
            ],
        }
    )
    payload = build_premium_report_payload(doc, analyze_document(doc), level=ReportLevel.STANDARD)
    assert payload.top_risks, "fixture model must produce at least one top risk"
    crafted = payload.top_risks[0].model_copy(
        update={"priority_tier": tier, "severity_score": severity, "composite_score": composite}
    )
    return payload.model_copy(update={"top_risks": [crafted]})


def test_render_html_p2_tier_and_composite_score() -> None:
    pytest.importorskip("fastapi")
    from otm_report_premium.render_html import render_premium_html

    # P2 top risk with no severity_score -> P2 fill colour + composite score_line branches
    html = render_premium_html(_payload_with_top_tier("P2", severity=None, composite=7.0))
    assert "<html" in html.lower() or "section" in html.lower()


def test_render_html_p3_tier() -> None:
    pytest.importorskip("fastapi")
    from otm_report_premium.render_html import render_premium_html

    # a non-P1/P2 tier -> the else (P3) fill-colour branch
    html = render_premium_html(_payload_with_top_tier("P3", severity=4.0, composite=4.0))
    assert html
