"""Only the canonical document supplies decisions, even outside the scored top ten."""

from __future__ import annotations

import re
from io import BytesIO
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from markdown_it import MarkdownIt
from otm_api.main import app
from otm_core_schema import Mitigation, Threat, TreatmentStatus, load_document_from_yaml_path
from otm_exporters import export_document_markdown
from otm_report_premium import build_premium_report_payload, render_premium_html, render_premium_markdown
from otm_report_premium.enums import ReportLevel
from otm_threat_engine import analyze_document, build_remediation_backlog
from otm_threat_engine.result import AnalysisResult

MINIMAL = Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml"


@pytest.fixture(scope="module")
def model_and_analysis():
    doc = load_document_from_yaml_path(MINIMAL)
    threats = [
        Threat.model_validate(
            {
                "id": f"decision_{status.value}",
                "title": "Orders API",
                "stride": "spoofing",
                "treatment_status": status,
                "treatment_notes": f"Review for {status.value}.",
                "risk": {"likelihood": 1, "impact": 1},
            }
        )
        for status in TreatmentStatus
    ]
    # Omitting both treatment fields is valid for a pre-existing document.
    threats.append(Threat.model_validate({"id": "legacy", "title": "Orders API", "stride": "spoofing"}))
    threats.append(
        Threat.model_validate(
            {
                "id": "no_score",
                "title": "Orders API",
                "stride": "spoofing",
                "treatment_status": "in_progress",
                "treatment_notes": "Keep <condition> & **literal**.\n\n## Follow-up",
            }
        )
    )
    doc = doc.model_copy(update={"threats": threats})
    return doc, analyze_document(doc)


@pytest.mark.parametrize("level", list(ReportLevel))
@pytest.mark.parametrize(
    ("locale", "heading", "absent"),
    [
        ("pt-BR", "Tratamento das ameaças declaradas", "Sem justificativa registrada."),
        ("en", "Declared threat treatment", "No rationale recorded."),
    ],
)
def test_premium_lists_each_decision_once_even_without_a_score(model_and_analysis, level, locale, heading, absent):
    doc, result = model_and_analysis
    payload = build_premium_report_payload(doc, result, level=level, locale=locale)
    report = render_premium_markdown(payload)
    section = report.split("## " + heading + "\n", 1)[1].split("\n## ", 1)[0]
    assert "no_score" not in {risk.threat_id for risk in payload.top_risks}
    assert all(section.count(f"`{threat.id}`") == 1 for threat in doc.threats)
    labels = {
        "pt-BR": [
            "Nova",
            "Triada",
            "Em andamento",
            "Mitigada",
            "Risco aceito",
            "Falso positivo",
            "Sem correção prevista",
        ],
        "en": ["New", "Triaged", "In progress", "Mitigated", "Accepted risk", "False positive", "Won’t fix"],
    }
    for status, label in zip(TreatmentStatus, labels[locale], strict=True):
        row = section.split(f"`decision_{status.value}`", 1)[1].split("\n- **", 1)[0]
        assert label in row and f"Review for {status.value}." in MarkdownIt().render(row)
    assert all(f"`{suggestion.id}`" not in section for suggestion in result.heuristic_threats)
    legacy = section.split("`legacy`", 1)[1].split("\n- **", 1)[0]
    assert ("Nova" if locale == "pt-BR" else "New") in legacy and absent in legacy
    rendered = MarkdownIt("commonmark", {"html": True}).render(section)
    assert "Keep &lt;condition&gt; &amp; **literal**. ## Follow-up" in rendered
    assert "<h2>" not in rendered


def test_pdf_source_preserves_association_and_quotes_human_text(model_and_analysis):
    doc, result = model_and_analysis
    payload = build_premium_report_payload(doc, result, level=ReportLevel.EXECUTIVE, locale="en")
    html = render_premium_html(payload)
    section = html.split("<h2>Declared threat treatment</h2>", 1)[1].split("</section>", 1)[0]
    assert "Keep &lt;condition&gt; &amp; **literal**." in section
    assert "No rationale recorded." in section
    assert re.search(r"decision_accepted_risk.*?Accepted risk.*?Review for accepted_risk\.", section, re.S)
    for threat in doc.threats:
        assert section.count(f"<code>{threat.id}</code>") == 1


def test_document_report_renders_missing_note_and_literal_note_with_its_own_threat(model_and_analysis):
    doc, _ = model_and_analysis
    threats = list(doc.threats)
    threats[-2] = threats[-2].model_copy(update={"treatment_notes": "   "})
    doc = doc.model_copy(update={"threats": threats})
    report = export_document_markdown(doc, locale="pt-BR")
    legacy = report.split("(`legacy`)", 1)[1].split("\n- **", 1)[0]
    assert "Nova" in legacy and "Sem justificativa registrada." in legacy
    plain = MarkdownIt("commonmark", {"html": True}).render(report)
    assert "Keep &lt;condition&gt; &amp; **literal**. ## Follow-up" in plain


def test_model_with_only_suggestions_never_displays_a_recorded_decision():
    doc = load_document_from_yaml_path(MINIMAL)
    analysis = analyze_document(doc)
    assert analysis.heuristic_threats
    payload = build_premium_report_payload(doc, analysis, level=ReportLevel.STANDARD, locale="en")
    assert "No declared threats in this model." in render_premium_markdown(payload)
    assert "No declared threats in this model." in render_premium_html(payload)


def test_unified_api_preserves_decisions_in_both_formats(model_and_analysis):
    pytest.importorskip("reportlab")
    pypdf = pytest.importorskip("pypdf")
    doc, result = model_and_analysis
    body = {
        "document": doc.model_dump(mode="json"),
        "analysis": result.model_dump(mode="json"),
        "locale": "pt-BR",
    }
    client = TestClient(app)
    md = client.post("/v1/reports", json=body)
    pdf = client.post("/v1/reports", json={**body, "output_format": "pdf"})
    assert md.status_code == pdf.status_code == 200
    assert md.headers["content-type"].startswith("text/markdown")
    assert pdf.headers["content-type"] == "application/pdf"
    reader = pypdf.PdfReader(BytesIO(pdf.content))
    text = " ".join(" ".join(p.extract_text().split()) for p in reader.pages)
    cover = " ".join(reader.pages[0].extract_text().split())
    total = build_premium_report_payload(doc, result, level=ReportLevel.STANDARD).executive_summary.threat_count
    assert f"**Total de ameaças** — {total}" in md.text
    assert f"{total} ameaças no total" in cover
    for phrase in (
        f"{total - 4} a triar ou tratar",
        "1 com risco aceito",
        "1 com mitigação declarada",
        "1 classificada como falso positivo",
        "1 sem correção prevista",
    ):
        assert phrase in cover and phrase in md.text
    assert "Resumo executivo" in md.text and "RESUMO EXECUTIVO" in text
    assert "Tratamento das ameaças declaradas" in md.text
    assert "Sem justificativa registrada." in md.text and "Sem justificativa registrada." in text
    assert [destination.title for destination in reader.outline] == [
        "Resumo executivo",
        "Priorização",
        "Tratamento de riscos",
        "Contexto técnico",
        "Revisão técnica",
    ]
    assert "Severidade da exposição ativa" in text
    assert "Decisões de tratamento" in text
    assert "Arquitetura do modelo" in text
    assert "Keep <condition> & **literal**. ## Follow-up" in text
    for report in (text, md.text):
        assert f"Exposição ativa: {total}" in report
        assert "Fila de revisão de riscos aceitos" in report
        assert "Responsável: não informado" in report
        assert "Data de revisão: não informado" in report
        assert "Verificação pendente" in report or "Verificar a eficácia" in report
        assert "Pendência sem pontuação" in report
    ranking = md.text.split("## Riscos prioritários", 1)[1].split("## Tratamento", 1)[0]
    assert "`decision_accepted_risk`" not in ranking

    rerun = client.post("/v1/reports", json={"document": body["document"], "run_analysis": True})
    assert rerun.status_code == 200
    assert "Análise gerada na exportação" in rerun.text
    assert "Análise gerada na exportação" not in md.text


def test_unified_api_keeps_accepted_risk_review_details_in_both_formats(model_and_analysis):
    pytest.importorskip("reportlab")
    pypdf = pytest.importorskip("pypdf")
    doc, _ = model_and_analysis
    owner, date = "Equipe de Arquitetura", "2027-01-20"
    threats = [
        threat.model_copy(update={"assignee": owner, "metadata": {"risk_review_date": date}})
        if threat.treatment_status == TreatmentStatus.ACCEPTED_RISK
        else threat
        for threat in doc.threats
    ]
    document = doc.model_copy(update={"threats": threats}).model_dump(mode="json")
    body = {"document": document, "locale": "pt-BR", "run_analysis": True}

    with TestClient(app) as client:
        markdown = client.post("/v1/reports", json=body)
        pdf = client.post("/v1/reports", json={**body, "output_format": "pdf"})

    assert markdown.status_code == pdf.status_code == 200
    pages = pypdf.PdfReader(BytesIO(pdf.content)).pages
    pdf_text = " ".join(word for page in pages for word in page.extract_text().split())
    for report in (markdown.text, pdf_text):
        _, queue = report.split("Fila de revisão de riscos aceitos", 1)
        assert f"Responsável: {owner}" in queue
        assert f"Data de revisão: {date}" in queue


@pytest.mark.parametrize(
    ("status", "outcome", "has_reference", "mitigation_status", "notes", "destination"),
    [
        ("new", None, False, "planned", None, "action"),
        ("triaged", None, False, "planned", None, "action"),
        ("in_progress", None, False, "planned", None, "action"),
        ("accepted_risk", None, False, "planned", None, "review_accepted"),
        ("wont_fix", None, False, "planned", "Review later.", "review_no_fix"),
        ("mitigated", None, False, "verified", None, "verify_mitigation"),
        ("mitigated", "risk_closed", True, "implemented", None, "verify_mitigation"),
        ("mitigated", "residual_risk", True, "verified", None, "verify_mitigation"),
        ("mitigated", "risk_closed", True, "verified", None, "history"),
        ("false_positive", None, False, "planned", "Review later.", "confirm_false_positive"),
        ("false_positive", "false_positive_confirmed", True, "planned", "   ", "confirm_false_positive"),
        ("false_positive", "false_positive_confirmed", True, "planned", "Out of scope.", "history"),
    ],
)
def test_exposure_and_ranking_use_the_same_recorded_decision(
    status, outcome, has_reference, mitigation_status, notes, destination
):
    doc = load_document_from_yaml_path(MINIMAL)
    target = doc.components[0]
    boundary = doc.trust_boundaries[0]
    target = target.model_copy(update={"in_trust_boundary": boundary.id})
    threat = Threat.model_validate(
        {
            "id": "critical_decision",
            "title": "Orders API",
            "stride": "spoofing",
            "target_component_id": target.id,
            "risk": {"likelihood": 5, "impact": 5},
            "treatment_status": status,
            "treatment_notes": notes,
            "assignee": "Architecture team",
            "metadata": {
                "risk_review_date": "2026-12-10",
                "treatment_verification": {"outcome": outcome, "reference": "QA-42" if has_reference else " "},
            },
        }
    )
    mitigation = Mitigation.model_validate(
        {
            "id": "reviewed_control",
            "title": "Tested control",
            "status": mitigation_status,
            "threat_ids": [threat.id],
        }
    )
    doc = doc.model_copy(
        update={
            "components": [target, *doc.components[1:]],
            "threats": [threat],
            "mitigations": [mitigation],
        }
    )
    result = AnalysisResult(engine_version="test", document_title=doc.metadata.title)
    report = build_premium_report_payload(doc, result, level=ReportLevel.STANDARD, consolidated=True)

    active = destination != "history"
    ranked = destination not in ("history", "review_accepted")
    assert report.executive_summary.threat_count == 1
    assert report.exposure_count == int(active)
    assert report.ranking_candidate_count == int(ranked)
    assert report.executive_summary.urgency_level == ("high" if active else "low")
    assert report.executive_summary.severity_distribution == ({"critical": 1} if active else {})
    assert report.distributions.heatmap_stride_severity == ({"spoofing": {"critical": 1}} if active else {})
    assert report.distributions.by_trust_boundary == ({boundary.name: 1} if active else {})
    assert [row.threat_id for row in report.top_risks] == ([threat.id] if ranked else [])
    (decision,) = report.declared_treatments
    assert decision.destination == destination
    assert decision.verification_reference == ("QA-42" if not active else None)
    assert decision.assignee == "Architecture team" and decision.review_date == "2026-12-10"


def test_closing_one_suggestion_does_not_hide_another_with_the_same_target():
    doc = load_document_from_yaml_path(MINIMAL)
    original = analyze_document(doc)
    suggestion = next(h for h in original.heuristic_threats if h.target_component_id and not h.skipped_as_duplicate)
    threat = Threat.model_validate(
        {
            **suggestion.model_dump(include={"id", "title", "stride", "target_component_id"}),
            "risk": {"likelihood": 5, "impact": 5},
            "treatment_status": "false_positive",
            "treatment_notes": "Confirmed for this specific suggestion.",
            "metadata": {
                "source": "otm_threat_engine",
                "engine_heuristic": True,
                "treatment_verification": {"outcome": "false_positive_confirmed", "reference": "QA-42"},
            },
        }
    )
    others = suggestion.model_copy(update={"id": "another_check", "skipped_as_duplicate": True})
    same = suggestion.model_copy(update={"skipped_as_duplicate": True})
    result = original.model_copy(update={"heuristic_threats": [same, others]})
    doc = doc.model_copy(update={"threats": [threat]})
    report = build_premium_report_payload(doc, result, level=ReportLevel.STANDARD, consolidated=True)
    assert report.executive_summary.threat_count == 2 and report.exposure_count == 1
    assert [risk.threat_id for risk in report.top_risks] == [others.id]
    assert all(h.skipped_as_duplicate for h in result.heuristic_threats)


@pytest.mark.parametrize(
    ("example", "maximum_positions"),
    [
        (
            "ecommerce-subscription",
            {
                "biz_payment_entitlement_mismatch": 5,
                "biz_webhook_replay_economic_abuse": 5,
                "biz_cancel_without_entitlement_revocation": 10,
            },
        ),
        (
            "finance-wallet",
            {
                "biz_double_submission_financial_action": 5,
                "biz_webhook_replay_economic_abuse": 5,
                "biz_balance_transaction_inconsistency": 10,
            },
        ),
        (
            "health-clinic",
            {
                "eng_flow_record_db_tampering": 5,
                "eng_medical_record_service_elevation_of_privilege": 5,
                "eng_ehr_db_information_disclosure": 10,
            },
        ),
    ],
)
def test_unified_ranking_keeps_model_priorities_and_group_references(example, maximum_positions):
    doc = load_document_from_yaml_path(MINIMAL.parent / "test-apps" / f"{example}.otm.yaml")
    analysis = analyze_document(doc, methodology="stride")
    report = build_premium_report_payload(doc, analysis, level=ReportLevel.STANDARD, consolidated=True)
    backlog = build_remediation_backlog(analysis, doc)

    positions = {risk.threat_id: risk.rank for risk in report.top_risks}
    assert all(positions.get(threat_id, 11) <= limit for threat_id, limit in maximum_positions.items())
    assert len(positions) == len(report.top_risks) == 10
    for group in report.root_cause_groups:
        items = [item for item in backlog.items if item.grouped_root_cause == group.key]
        assert group.backlog_item_ids == [item.id for item in items]
        assert {(ref.kind, ref.id) for ref in group.finding_refs} == {
            (ref.kind, ref.id) for item in items for ref in item.related_findings
        }


def test_default_pdf_preserves_a_decision_across_pages(model_and_analysis):
    pytest.importorskip("reportlab")
    pypdf = pytest.importorskip("pypdf")
    doc, _ = model_and_analysis
    decision = doc.threats[0].model_copy(
        update={"treatment_notes": ("Verificação arquivada. " * 450 + "Última frase da justificativa extensa.")}
    )
    doc = doc.model_copy(update={"threats": [decision]})
    body = {"document": doc.model_dump(mode="json"), "run_analysis": True, "output_format": "pdf"}
    result = TestClient(app).post("/v1/reports", json=body)
    assert result.status_code == 200
    reader = pypdf.PdfReader(BytesIO(result.content))
    text_pages = [" ".join(page.extract_text().split()) for page in reader.pages]
    assert sum("Verificação arquivada." in page for page in text_pages) >= 2
    assert sum(page.count("arquivada.") for page in text_pages) == 450
    assert "Última frase da justificativa extensa." in " ".join(text_pages)
