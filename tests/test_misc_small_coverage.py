"""Coverage — document markdown empty sections + recommendation-gate anchors."""

from __future__ import annotations

from otm_core_schema import create_blank_document
from otm_core_schema.document import Asset, Component
from otm_core_schema.enums import AssetKind, ComponentKind
from otm_exporters import export_document_markdown
from otm_threat_engine.recommendation_gate import (
    _has_payment_anchor,
    _has_upload_anchor,
)


def test_document_markdown_empty_sections() -> None:
    # No components / flows / boundaries -> each section's early-return is taken.
    doc = create_blank_document().model_copy(update={"components": [], "data_flows": [], "trust_boundaries": [], "assets": []})
    md = export_document_markdown(doc)
    assert isinstance(md, str)


def test_document_markdown_full() -> None:
    md = export_document_markdown(create_blank_document())
    assert isinstance(md, str)


def test_payment_anchor_via_financial_asset() -> None:
    doc = create_blank_document().model_copy(
        update={"assets": [Asset(id="fin", name="Ledger", asset_kind=AssetKind.FINANCIAL_RECORD)]}
    )
    assert _has_payment_anchor(doc) is True


def test_payment_anchor_via_component_name() -> None:
    doc = create_blank_document().model_copy(
        update={"components": [Component(id="payment_svc", name="Payment", kind=ComponentKind.PROCESS)], "assets": []}
    )
    assert _has_payment_anchor(doc) is True


def test_no_payment_anchor() -> None:
    doc = create_blank_document().model_copy(update={"assets": [], "components": []})
    assert _has_payment_anchor(doc) is False


def test_upload_anchor_via_corpus() -> None:
    d = create_blank_document().model_dump(mode="python", by_alias=True)
    d.setdefault("metadata", {})["summary"] = "users upload arquivo to s3 storage"
    doc = create_blank_document().__class__.model_validate(d)
    assert _has_upload_anchor(doc) is True
