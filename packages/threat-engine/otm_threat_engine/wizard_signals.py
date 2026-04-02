"""
Sinais normalizados a partir de `metadata.tags` com prefixo `wz:` (assistente web).

O motor consome estes sinais para:
- enriquecer o corpus usado em anti-patterns (evidência positiva declarada pelo modelador);
- ajustar parcialmente o ranking de risco (explicável, conservador).

Formato: `wz:<template_semantic_profile>:<prompt_id>=yes|no|unk`
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from typing import Any

from otm_core_schema import ThreatModelDocument
from otm_core_schema.document import RiskAssessment
from otm_threat_engine.risk_calc import build_risk_assessment

_TAG_RE = re.compile(
    r"^wz:(?P<profile>[a-z0-9_]+):(?P<key>[a-z0-9_]+)=(?P<val>yes|no|unk)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class WizardSignal:
    """Um par pergunta/resposta normalizado."""

    profile: str
    key: str
    value: str  # yes | no | unk


def parse_wizard_tags(tags: list[str] | None) -> list[WizardSignal]:
    """Extrai apenas tags `wz:` válidas."""
    out: list[WizardSignal] = []
    for raw in tags or []:
        m = _TAG_RE.match((raw or "").strip())
        if not m:
            continue
        out.append(
            WizardSignal(
                profile=m.group("profile").lower(),
                key=m.group("key").lower(),
                value=m.group("val").lower(),
            )
        )
    return out


def signals_for_profile(doc: ThreatModelDocument) -> list[WizardSignal]:
    """Sinais cujo perfil coincide com `template_semantic_profile` do modelo."""
    want = (doc.model_info.template_semantic_profile or "").strip().lower()
    if not want:
        return []
    return [s for s in parse_wizard_tags(doc.metadata.tags) if s.profile == want]


def synthetic_keyword_corpus(signals: list[WizardSignal]) -> str:
    """
    Palavras-chave sintéticas para o anti-pattern matcher quando o modelador
    confirma controlos (resposta `yes` a perguntas de mitigação).
    """
    chunks: list[str] = []
    for s in signals:
        if s.value != "yes":
            continue
        if s.profile == "internal_admin_portal":
            if s.key == "approval":
                chunks.extend(["aprovação", "approval", "workflow", "four-eyes"])
            if s.key == "segregation":
                chunks.extend(["segregação", "segregation", "duty", "funções"])
            if s.key == "jit":
                chunks.extend(["just-in-time", "jit", "elevação", "temporary"])
        elif s.profile == "file_handling_application":
            if s.key == "quarantine":
                chunks.extend(["quarentena", "quarantine", "isolamento"])
            if s.key == "scan":
                chunks.extend(["antivirus", "sandbox", "revalidação", "scan"])
            if s.key == "public_objects":
                chunks.extend(["privado", "signed", "acl", "não público"])
        elif s.profile == "api_backend_rest":
            if s.key == "auth":
                chunks.extend(["oauth", "autenticação", "authorization", "api key"])
            if s.key == "rate_limit":
                chunks.extend(["rate limit", "throttl", "quota"])
            if s.key == "edge_controls":
                chunks.extend(["waf", "policy", "perímetro", "gateway policy"])
        elif s.profile == "industry_ecommerce":
            if s.key == "checkout":
                chunks.extend(["checkout", "contexto", "fraud"])
            if s.key == "psp_boundary":
                chunks.extend(["psp", "terceiro", "third", "pagamento"])
            if s.key == "sensitive_data":
                chunks.extend(["classificação", "pci", "dados sensíveis"])
    return " ".join(chunks).lower()


def _boost_impact(r: RiskAssessment, delta: int) -> RiskAssessment:
    ni = min(5, r.impact + delta)
    return build_risk_assessment(r.likelihood, ni)


def _admin_risk_signal(signals: list[WizardSignal]) -> bool:
    """Ausência de aprovação ou segregação declarada pelo modelador."""
    for s in signals:
        if s.profile != "internal_admin_portal":
            continue
        if s.key == "approval" and s.value == "no":
            return True
        if s.key == "segregation" and s.value == "no":
            return True
    return False


def _file_risk_signal(signals: list[WizardSignal]) -> bool:
    for s in signals:
        if s.profile != "file_handling_application":
            continue
        if s.key == "quarantine" and s.value == "no":
            return True
        if s.key == "scan" and s.value == "no":
            return True
        if s.key == "public_objects" and s.value == "yes":
            return True
    return False


def _api_risk_signal(signals: list[WizardSignal]) -> bool:
    for s in signals:
        if s.profile != "api_backend_rest":
            continue
        if s.key == "auth" and s.value == "no":
            return True
        if s.key == "rate_limit" and s.value == "no":
            return True
        if s.key == "edge_controls" and s.value == "no":
            return True
    return False


def _ecom_risk_signal(signals: list[WizardSignal]) -> bool:
    for s in signals:
        if s.profile != "industry_ecommerce":
            continue
        if s.key == "psp_boundary" and s.value == "no":
            return True
        if s.key == "sensitive_data" and s.value == "no":
            return True
        if s.key == "checkout" and s.value == "no":
            return True
    return False


def _matches_admin_context(h: Any) -> bool:
    blob = f"{h.id} {h.title} {h.description}".lower()
    return h.id.startswith("biz_") or "admin" in blob or "privileg" in blob or "auditoria" in blob


def _matches_upload_context(h: Any) -> bool:
    blob = f"{h.id} {h.title} {h.description}".lower()
    return "upload" in blob or "ficheiro" in blob or "file" in blob or "malware" in blob


def _matches_api_perimeter(h: Any) -> bool:
    blob = f"{h.id} {h.title} {h.description}".lower()
    return "gateway" in blob or "api" in blob or "rate" in blob or "denial" in blob or "ddos" in blob


def _matches_payment_context(h: Any) -> bool:
    blob = f"{h.id} {h.title} {h.description}".lower()
    return "pagamento" in blob or "payment" in blob or "checkout" in blob or "psp" in blob


def apply_wizard_context_to_heuristics(
    doc: ThreatModelDocument,
    heuristics: list[Any],
) -> tuple[int, list[str]]:
    """
    Aumenta impacto (conservador, +1) quando sinais negativos do assistente reforçam o contexto.

    Devolve (n_alterados, notas_explicativas).
    """
    sigs = signals_for_profile(doc)
    if not sigs:
        return 0, []

    notes: list[str] = []
    admin = _admin_risk_signal(sigs)
    file_r = _file_risk_signal(sigs)
    api_r = _api_risk_signal(sigs)
    ecom = _ecom_risk_signal(sigs)

    if admin:
        notes.append(
            "Assistente: ausência de aprovação/segregação declarada — reforço conservador em achados admin/privilégio."
        )
    if file_r:
        notes.append(
            "Assistente: quarentena/scan ausentes ou exposição pública — reforço em achados de ficheiro/upload."
        )
    if api_r:
        notes.append(
            "Assistente: auth/rate/WAF fracos declarados — reforço em achados de perímetro/API."
        )
    if ecom:
        notes.append(
            "Assistente: checkout/PSP/dados sensíveis em risco declarado — reforço em achados de pagamento."
        )

    changed = 0
    for h in heuristics:
        if h.skipped_as_duplicate:
            continue
        boost = 0
        if admin and _matches_admin_context(h):
            boost = 1
        elif file_r and _matches_upload_context(h):
            boost = 1
        elif api_r and _matches_api_perimeter(h):
            boost = 1
        elif ecom and _matches_payment_context(h):
            boost = 1
        if boost:
            h.risk = _boost_impact(h.risk, boost)
            ref = "wizard:context_boost"
            if ref not in h.signal_refs:
                h.signal_refs = [*list(h.signal_refs), ref]
            changed += 1

    return changed, notes
