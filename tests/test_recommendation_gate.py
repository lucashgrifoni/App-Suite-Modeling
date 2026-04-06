"""Filtro anti-leakage de hints de pack."""

from __future__ import annotations

from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_core_schema.io import load_document_from_yaml
from otm_industry_packs.loader import load_pack, load_template_yaml
from otm_threat_engine.recommendation_gate import filter_pack_control_hints

_ROOT = Path(__file__).resolve().parents[1]


def test_finance_pack_drops_payment_hints_on_admin_portal_without_payment_anchor() -> None:
    raw = load_template_yaml("admin-portal")
    doc = load_document_from_yaml(raw)
    hints = load_pack("finance").control_hints or []
    filtered = filter_pack_control_hints(doc, list(hints))
    assert not any("pagamento" in h.lower() or "payment" in h.lower() for h in filtered)


def test_finance_pack_keeps_payment_hints_when_model_describes_payment() -> None:
    raw = load_template_yaml("payment-integration")
    doc = load_document_from_yaml(raw)
    hints = load_pack("finance").control_hints or []
    filtered = filter_pack_control_hints(doc, list(hints))
    assert len(filtered) >= 1


def test_upload_hints_require_upload_context() -> None:
    doc = load_document_from_yaml_path(_ROOT / "examples" / "minimal.otm.yaml")
    hints = ["Validar tipo MIME e quarentena antes de processar upload"]
    assert filter_pack_control_hints(doc, hints) == []


def test_entitlement_subscription_and_premium_hints_suppressed_without_commercial_signals() -> None:
    """
    Sem billing/payment/subscription/plan/entitlement no modelo: não passar hints de
    entitlement, plano premium ou benefício comercial.
    """
    doc = load_document_from_yaml_path(_ROOT / "examples" / "minimal.otm.yaml")
    hints = [
        "Auditar mapeamento entitlement premium vs plano contratado no billing",
        "Rever benefício de assinatura e upsell no catálogo comercial",
        "Controlar pricing tier e license tier entre serviços",
    ]
    assert filter_pack_control_hints(doc, hints) == []


def test_entitlement_hints_preserved_when_model_has_subscription_signals() -> None:
    doc = load_document_from_yaml_path(_ROOT / "examples" / "minimal.otm.yaml")
    doc = doc.model_copy(
        update={
            "metadata": doc.metadata.model_copy(
                update={"summary": "API REST com subscription e billing."}
            )
        }
    )
    hints = ["Validar entitlement entre plano premium e SKU"]
    out = filter_pack_control_hints(doc, hints)
    assert len(out) == 1
