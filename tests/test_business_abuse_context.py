from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_threat_engine.business_abuse_context import (
    build_business_abuse_context,
    first_component_id_with,
    first_flow_id_with,
)

_ROOT = Path(__file__).resolve().parents[1]
_ECOMMERCE = _ROOT / "examples" / "test-apps" / "ecommerce-subscription.otm.yaml"


def test_context_builder_detects_core_business_signals() -> None:
    doc = load_document_from_yaml_path(_ECOMMERCE)
    ctx = build_business_abuse_context(doc)
    assert ctx.has_payment
    assert ctx.has_entitlement
    assert ctx.has_coupon


def test_search_helpers_return_known_component_and_flow() -> None:
    doc = load_document_from_yaml_path(_ECOMMERCE)
    assert first_component_id_with(doc, "payment", "checkout") is not None
    assert first_flow_id_with(doc, "checkout", "webhook") is not None
