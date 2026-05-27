"""Heurísticas de classificação: STRIDE + componente → causa raiz, controlo, camada."""

from __future__ import annotations

from otm_core_schema import ComponentKind, StrideCategory, ThreatModelMethodology
from otm_core_schema.document import ThreatModelDocument

from otm_threat_engine.result import HeuristicThreat


def component_kind_for_id(doc: ThreatModelDocument | None, cid: str | None) -> ComponentKind | None:
    if not doc or not cid:
        return None
    for c in doc.components:
        if c.id == cid:
            return c.kind
    return None


def _ai_context(methodology: ThreatModelMethodology, threat: HeuristicThreat) -> bool:
    if methodology == ThreatModelMethodology.PLOT4AI:
        return True
    blob = f"{threat.title} {threat.description}".lower()
    return any(k in blob for k in ("llm", "modelo de linguagem", "prompt", "rag", "inferen"))


def _layer_for_kind(ck: ComponentKind | None) -> str | None:
    if ck in (ComponentKind.GATEWAY, ComponentKind.EXTERNAL_ENTITY):
        return "edge"
    if ck == ComponentKind.PROCESS:
        return "application"
    if ck in (ComponentKind.DATASTORE, ComponentKind.QUEUE):
        return "data"
    if ck == ComponentKind.USER:
        return "edge"
    return None


def _root_control_cat_for_stride(st: StrideCategory, ck: ComponentKind | None) -> tuple[str, str, str]:
    """Devolve (root_cause, control_type, category) por categoria STRIDE."""
    if st in (StrideCategory.SPOOFING, StrideCategory.ELEVATION_OF_PRIVILEGE):
        return "identity_and_authorization_gaps", "identity_access", "identity_access"
    if st == StrideCategory.INFORMATION_DISCLOSURE:
        return "data_exposure_and_classification", "data_protection", "data"
    if st == StrideCategory.TAMPERING:
        is_ds = ck == ComponentKind.DATASTORE
        return (
            "integrity_and_supply_chain",
            "data_protection" if is_ds else "hardening_and_integrity",
            "data" if is_ds else "surface_exposure",
        )
    if st == StrideCategory.DENIAL_OF_SERVICE:
        return "availability_and_resilience", "resilience_and_rate_limiting", "observability_audit"
    if st == StrideCategory.REPUDIATION:
        return "non_repudiation_and_audit", "logging_and_audit", "observability_audit"
    # pragma: no cover - unreachable: StrideCategory is exhaustive (all 6 handled above)
    return "general_mitigation", "defense_in_depth", "cross_cutting"  # pragma: no cover


def _supplier_trust_override(ck: ComponentKind | None, threat: HeuristicThreat) -> tuple[str, str, str, str] | None:
    """Override (cat, root, ctrl, layer_hint) quando a entidade externa é um fornecedor (supplier)."""
    if ck != ComponentKind.EXTERNAL_ENTITY or not threat.framework_refs:
        return None
    for ref in threat.framework_refs:
        if ref.framework and "supplier" in ref.framework.lower():
            return "third_party_integration", "third_party_trust", "vendor_and_integration_governance", "integration"
    return None


def classify_threat(
    threat: HeuristicThreat,
    doc: ThreatModelDocument | None,
    methodology: ThreatModelMethodology,
) -> tuple[str, str, str, str | None]:
    """
    Devolve:
    (grouped_root_cause, suggested_control_type, control_category, architecture_layer)
    """
    ck = component_kind_for_id(doc, threat.target_component_id)
    layer = _layer_for_kind(ck)
    root, ctrl, cat = _root_control_cat_for_stride(threat.stride, ck)

    override = _supplier_trust_override(ck, threat)
    if override is not None:
        cat, root, ctrl, layer_hint = override
        layer = layer or layer_hint

    if _ai_context(methodology, threat):
        cat = "ai_ml_specific"
        if root == "general_mitigation":  # pragma: no cover - root never "general_mitigation" (STRIDE exhaustive)
            root = "ai_governance_and_model_risk"
        ctrl = "ai_ml_governance" if ctrl == "defense_in_depth" else f"ai_ml:{ctrl}"

    return root, ctrl, cat, layer


def effort_for_threat(threat: HeuristicThreat, root: str) -> str:
    r = threat.risk.likelihood * threat.risk.impact
    if root in ("non_repudiation_and_audit", "general_mitigation") and r < 16:
        return "low"
    if threat.stride in (StrideCategory.ELEVATION_OF_PRIVILEGE, StrideCategory.TAMPERING) and r >= 16:
        return "high"
    if root.startswith("identity"):
        return "medium"
    return "medium"


def impact_level_from_risk(threat: HeuristicThreat) -> str:
    raw = threat.risk.score
    if raw is None:
        raw = float(threat.risk.likelihood * threat.risk.impact)
    else:
        raw = float(raw)
    if raw >= 16:
        return "high"
    if raw >= 9:
        return "medium"
    return "low"
