"""Coverage — rich deep report with pack + baseline + all severity bands.

Exercises builder severity-band/urgency/strategic branches, render_html quick-wins and
baseline-delta sections, and analysis_markdown pack-control / recommendation lines.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from otm_core_schema import create_blank_document, load_document_from_yaml_path

pytest.importorskip("fastapi")
from otm_api.services.reports_premium import render_premium  # noqa: E402
from otm_exporters import export_analysis_markdown  # noqa: E402
from otm_industry_packs.loader import load_pack  # noqa: E402
from otm_report_premium.enums import ReportFormat, ReportLevel  # noqa: E402
from otm_threat_engine import analyze_document  # noqa: E402

_ROOT = Path(__file__).resolve().parents[1]

_HAS_PDF = True
try:
    import xhtml2pdf  # noqa: F401
except Exception:  # pragma: no cover
    _HAS_PDF = False


def _rich_doc():
    d: dict[str, Any] = load_document_from_yaml_path(_ROOT / "examples" / "saas-ordering-v1.otm.yaml").model_dump(
        mode="python", by_alias=True
    )
    tb = (d.get("trust_boundaries") or [{"id": "internet"}])[0]["id"]
    d["components"].append({"id": "pay_gw", "name": "Payment GW", "kind": "gateway", "in_trust_boundary": tb})
    for fl in d.get("data_flows") or []:
        fl.update({"public_exposure": True, "affects_privileged_state": True, "encrypted": False})
    d.setdefault("model", {})["template_semantic_profile"] = "industry_ecommerce"
    return load_document_from_yaml_path(_ROOT / "examples" / "saas-ordering-v1.otm.yaml").__class__.model_validate(d)


def test_rich_deep_report_markdown_with_pack_and_baseline() -> None:
    doc = _rich_doc()
    pack = load_pack("saas")
    analysis = analyze_document(doc, pack=pack, auto_recommend=True)
    baseline = analyze_document(create_blank_document())
    md, _ = render_premium(
        doc, analysis, level=ReportLevel.DEEP, output_format=ReportFormat.MARKDOWN, baseline=baseline, locale="en"
    )
    assert md and "##" in md
    # analysis markdown should include pack-control / recommendation lines
    am = export_analysis_markdown(analysis, locale="en")
    assert am


@pytest.mark.skipif(not _HAS_PDF, reason="xhtml2pdf extra not installed")
def test_rich_deep_report_pdf_with_baseline() -> None:
    doc = _rich_doc()
    analysis = analyze_document(doc, pack=load_pack("saas"))
    baseline = analyze_document(create_blank_document())
    _, pdf = render_premium(
        doc, analysis, level=ReportLevel.DEEP, output_format=ReportFormat.PDF, baseline=baseline, locale="en"
    )
    assert pdf and len(pdf) > 100


def test_analysis_markdown_with_pack_hints() -> None:
    doc = _rich_doc()
    analysis = analyze_document(doc, pack=load_pack("saas"), auto_recommend=True)
    out = export_analysis_markdown(analysis)
    assert isinstance(out, str) and out
