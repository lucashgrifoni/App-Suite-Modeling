"""Treatment counts shown below the total on the standard report."""

from collections import Counter

from otm_core_schema import TreatmentStatus

from .i18n_locale import PremiumReportLocale
from .models import DeclaredThreatTreatment, PremiumReportPayload


def exposure_overview(payload: PremiumReportPayload) -> str:
    if payload.exposure_count is None:
        return ""
    urgency = payload.executive_summary.urgency_level
    has_scores = bool(payload.executive_summary.severity_distribution)
    if payload.locale == "pt-BR":
        label = {"high": "alta", "medium": "média", "low": "baixa"}[urgency] if has_scores else "sem cálculo"
        return f"Exposição ativa: {payload.exposure_count} · Urgência: {label}"
    return f"Active exposure: {payload.exposure_count} · Urgency: {urgency if has_scores else 'unavailable'}"


def pending_check(decision: DeclaredThreatTreatment | None, locale: PremiumReportLocale) -> str:
    if decision and decision.destination == "verify_mitigation":
        return "Verificação pendente" if locale == "pt-BR" else "Verification pending"
    if decision and decision.destination == "confirm_false_positive":
        return "Confirmação pendente" if locale == "pt-BR" else "Confirmation pending"
    return ""


def treatment_follow_up(decision: DeclaredThreatTreatment, locale: PremiumReportLocale) -> str:
    messages = {
        "action": ("Triar ou tratar", "Triage or treat"),
        "verify_mitigation": (
            "Verificar a eficácia e avaliar o risco residual",
            "Verify effectiveness and assess residual risk",
        ),
        "confirm_false_positive": ("Confirmar e justificar o falso positivo", "Confirm and justify the false positive"),
        "review_no_fix": (
            "Revisar a decisão de deixar o risco sem correção",
            "Review the decision to leave the risk without a fix",
        ),
        "review_accepted": ("Acompanhar a data de revisão do aceite", "Follow up on the risk acceptance review date"),
        "history": ("Preservado no histórico", "Retained in treatment history"),
    }
    if decision.destination is None:
        return ""
    return messages[decision.destination][0 if locale == "pt-BR" else 1]


def decision_details(decision: DeclaredThreatTreatment, locale: PremiumReportLocale) -> list[str]:
    if decision.destination is None:
        return []
    pt = locale == "pt-BR"
    details = [treatment_follow_up(decision, locale)]
    if decision.destination == "review_accepted":
        missing = "não informado" if pt else "not recorded"
        owner = "Responsável" if pt else "Owner"
        review = "Data de revisão" if pt else "Review date"
        details.extend([f"{owner}: {decision.assignee or missing}", f"{review}: {decision.review_date or missing}"])
    if not decision.has_score and decision.destination not in ("review_accepted", "history"):
        details.append("Pendência sem pontuação" if pt else "Unscored action item")
    if decision.verification_reference:
        label = "Referência da verificação" if pt else "Verification reference"
        details.append(f"{label}: {decision.verification_reference}")
    return details


def decision_sections(
    decisions: list[DeclaredThreatTreatment],
    locale: PremiumReportLocale,
) -> list[tuple[str, list[DeclaredThreatTreatment]]]:
    pt = locale == "pt-BR"
    return [
        ("", [d for d in decisions if d.destination not in ("review_accepted", "history")]),
        (
            "Fila de revisão de riscos aceitos" if pt else "Accepted risk review queue",
            sorted(
                (d for d in decisions if d.destination == "review_accepted"),
                key=lambda d: (d.review_date is None, d.review_date or ""),
            ),
        ),
        (
            "Histórico de tratamento" if pt else "Treatment history",
            [d for d in decisions if d.destination == "history"],
        ),
    ]


def treatment_overview(payload: PremiumReportPayload) -> str:
    """Describe recorded states and suggestions awaiting triage without using risk scores."""
    states = Counter(decision.treatment_status for decision in payload.declared_treatments)
    accepted = states[TreatmentStatus.ACCEPTED_RISK]
    mitigated = states[TreatmentStatus.MITIGATED]
    false_positive = states[TreatmentStatus.FALSE_POSITIVE]
    wont_fix = states[TreatmentStatus.WONT_FIX]
    pending = payload.executive_summary.threat_count - accepted - mitigated - false_positive - wont_fix
    counts = (pending, accepted, mitigated, false_positive, wont_fix)
    labels = (
        (
            "a triar ou tratar",
            "com risco aceito",
            "com mitigação declarada",
            "classificada como falso positivo" if false_positive == 1 else "classificadas como falso positivo",
            "sem correção prevista",
        )
        if payload.locale == "pt-BR"
        else (
            "awaiting triage or treatment",
            "with accepted risk",
            "with mitigation recorded",
            "classified as a false positive" if false_positive == 1 else "classified as false positives",
            "with no fix planned",
        )
    )
    items = (f"{count} {label}" for count, label in zip(counts, labels, strict=True) if count)
    return " · ".join(items)
