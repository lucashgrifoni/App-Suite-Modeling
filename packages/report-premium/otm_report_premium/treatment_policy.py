"""The unified report's interpretation of recorded treatment decisions."""

from datetime import date

from otm_core_schema import MitigationStatus, ThreatModelDocument, TreatmentStatus
from otm_core_schema.document import Threat
from otm_core_schema.enums import StrideCategory
from otm_exporters.markdown_text import md_inline
from otm_threat_engine.result import HeuristicThreat

from .models import DeclaredThreatTreatment, TreatmentDestination


def _nonblank(value: object) -> str | None:
    return (md_inline(value).strip() or None) if isinstance(value, str) else None


def _review_date(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    try:
        return value if date.fromisoformat(value).isoformat() == value else None
    except ValueError:
        return None


def _verified_destination(
    threat: Threat,
    verified_mitigation: bool,
) -> tuple[TreatmentDestination, str | None]:
    verification = threat.metadata.get("treatment_verification")
    reference = _nonblank(verification.get("reference")) if isinstance(verification, dict) else None
    outcome = verification.get("outcome") if isinstance(verification, dict) else None
    if threat.treatment_status == TreatmentStatus.MITIGATED:
        closed = outcome == "risk_closed" and verified_mitigation and reference is not None
        return ("history", reference) if closed else ("verify_mitigation", None)
    confirmed = outcome == "false_positive_confirmed" and reference is not None and _nonblank(threat.treatment_notes)
    return ("history", reference) if confirmed else ("confirm_false_positive", None)


def report_treatment_decisions(document: ThreatModelDocument) -> list[DeclaredThreatTreatment]:
    verified = {
        threat_id
        for mitigation in document.mitigations
        if mitigation.status == MitigationStatus.VERIFIED
        for threat_id in mitigation.threat_ids
    }
    decisions = []
    for threat in document.threats:
        status = threat.treatment_status
        destination: TreatmentDestination = "action"
        reference = None
        if status == TreatmentStatus.ACCEPTED_RISK:
            destination = "review_accepted"
        elif status == TreatmentStatus.WONT_FIX:
            destination = "review_no_fix"
        elif status in (TreatmentStatus.MITIGATED, TreatmentStatus.FALSE_POSITIVE):
            destination, reference = _verified_destination(threat, threat.id in verified)
        decisions.append(
            DeclaredThreatTreatment(
                id=threat.id,
                title=threat.title,
                treatment_status=status,
                treatment_notes=threat.treatment_notes,
                destination=destination,
                has_score=threat.risk is not None,
                assignee=_nonblank(threat.assignee),
                review_date=_review_date(threat.metadata.get("risk_review_date")),
                verification_reference=reference,
            )
        )
    return decisions


def _target(threat: Threat | HeuristicThreat) -> tuple[str | None, str | None, StrideCategory]:
    # Mirrors the engine's coverage key. Provenance matching also checks the asset and source.
    return threat.target_component_id, threat.target_data_flow_id, threat.stride


def report_suggestions(
    threats: list[Threat],
    suggestions: list[HeuristicThreat],
    outside_action: set[str],
) -> list[HeuristicThreat]:
    """Keep unrelated suggestions visible when the declaration that covered them leaves action."""
    declared = {threat.id: threat for threat in threats}
    action_coverage = {_target(t) for t in threats if t.risk is not None and t.id not in outside_action}
    detached_coverage = {_target(t) for t in threats if t.risk is not None and t.id in outside_action}
    reconsider = detached_coverage - action_coverage
    included = []
    for suggestion in suggestions:
        record = declared.get(suggestion.id)
        if (
            record
            and record.metadata.get("engine_heuristic") is True
            and record.metadata.get("source") == "otm_threat_engine"
            and _target(record) == _target(suggestion)
            and record.target_asset_id == suggestion.target_asset_id
        ):
            continue
        if suggestion.skipped_as_duplicate and _target(suggestion) not in reconsider:
            continue
        if suggestion.skipped_as_duplicate or record:
            # The report projection keeps the source object and its ID intact.
            suggestion = suggestion.model_copy(
                update={
                    "id": f"suggestion:{suggestion.id}" if record else suggestion.id,
                    "skipped_as_duplicate": False,
                }
            )
        included.append(suggestion)
    return included
