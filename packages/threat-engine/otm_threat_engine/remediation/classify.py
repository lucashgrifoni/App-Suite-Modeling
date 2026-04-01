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
    layer: str | None = None
    if ck in (ComponentKind.GATEWAY, ComponentKind.EXTERNAL_ENTITY):
        layer = "edge"
    elif ck == ComponentKind.PROCESS:
        layer = "application"
    elif ck in (ComponentKind.DATASTORE, ComponentKind.QUEUE):
        layer = "data"
    elif ck == ComponentKind.USER:
        layer = "edge"

    st = threat.stride

    if st in (StrideCategory.SPOOFING, StrideCategory.ELEVATION_OF_PRIVILEGE):
        root = "identity_and_authorization_gaps"
        ctrl = "identity_access"
        cat = "identity_access"
    elif st == StrideCategory.INFORMATION_DISCLOSURE:
        root = "data_exposure_and_classification"
        ctrl = "data_protection"
        cat = "data"
    elif st == StrideCategory.TAMPERING:
        root = "integrity_and_supply_chain"
        ctrl = "data_protection" if ck == ComponentKind.DATASTORE else "hardening_and_integrity"
        cat = "data" if ck == ComponentKind.DATASTORE else "surface_exposure"
    elif st == StrideCategory.DENIAL_OF_SERVICE:
        root = "availability_and_resilience"
        ctrl = "resilience_and_rate_limiting"
        cat = "observability_audit"
    elif st == StrideCategory.REPUDIATION:
        root = "non_repudiation_and_audit"
        ctrl = "logging_and_audit"
        cat = "observability_audit"
    else:
        root = "general_mitigation"
        ctrl = "defense_in_depth"
        cat = "cross_cutting"

    if ck == ComponentKind.EXTERNAL_ENTITY and threat.framework_refs:
        for ref in threat.framework_refs:
            if ref.framework and "supplier" in ref.framework.lower():
                cat = "third_party_integration"
                root = "third_party_trust"
                ctrl = "vendor_and_integration_governance"
                layer = layer or "integration"
                break

    if _ai_context(methodology, threat):
        cat = "ai_ml_specific"
        if root == "general_mitigation":
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
