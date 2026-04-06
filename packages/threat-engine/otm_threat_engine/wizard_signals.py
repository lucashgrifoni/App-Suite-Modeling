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
from otm_threat_engine.wizard_audit_models import WizardSignalTraceEntry

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


def _admin_negative_count(signals: list[WizardSignal]) -> int:
    """Conta respostas negativas distintas no cluster admin (anti-overfitting: precisa ≥2 para armar boost)."""
    keys = {"approval", "segregation"}
    n = 0
    for s in signals:
        if s.profile != "internal_admin_portal":
            continue
        if s.key in keys and s.value == "no":
            n += 1
    return n


def _admin_mitigators(signals: list[WizardSignal]) -> list[WizardSignal]:
    return [s for s in signals if s.profile == "internal_admin_portal" and s.value == "yes"]


def _admin_risk_signal(signals: list[WizardSignal]) -> bool:
    """Requer ≥2 lacunas declaradas (ex.: approval=no e segregation=no) para não amplificar com 1 resposta isolada."""
    if _admin_negative_count(signals) < 2:
        return False
    # Mitigador forte: aprovação confirmada reduz confiança no boost — não arma.
    for s in signals:
        if s.profile == "internal_admin_portal" and s.key == "approval" and s.value == "yes":
            return False
    return True


def _file_risk_signal(signals: list[WizardSignal]) -> bool:
    """Combinação (quarantine=no e scan=no) OU exposição pública declarada (sinal único de alto valor)."""
    fh = [s for s in signals if s.profile == "file_handling_application"]
    q_no = any(s.key == "quarantine" and s.value == "no" for s in fh)
    sc_no = any(s.key == "scan" and s.value == "no" for s in fh)
    pub_yes = any(s.key == "public_objects" and s.value == "yes" for s in fh)
    return pub_yes or (q_no and sc_no)


def _api_negative_count(signals: list[WizardSignal]) -> int:
    keys = {"auth", "rate_limit", "edge_controls"}
    return sum(
        1
        for s in signals
        if s.profile == "api_backend_rest" and s.key in keys and s.value == "no"
    )


def _api_risk_signal(signals: list[WizardSignal]) -> bool:
    return _api_negative_count(signals) >= 2


def _ecom_negative_count(signals: list[WizardSignal]) -> int:
    keys = {"checkout", "psp_boundary", "sensitive_data"}
    return sum(
        1
        for s in signals
        if s.profile == "industry_ecommerce" and s.key in keys and s.value == "no"
    )


def _ecom_risk_signal(signals: list[WizardSignal]) -> bool:
    return _ecom_negative_count(signals) >= 2


def build_corpus_mitigation_trace(signals: list[WizardSignal]) -> list[WizardSignalTraceEntry]:
    """Uma entrada por resposta `yes` que injeta keywords no corpus anti-pattern."""
    out: list[WizardSignalTraceEntry] = []
    for s in signals:
        if s.value != "yes":
            continue
        tag = f"wz:{s.profile}:{s.key}=yes"
        out.append(
            WizardSignalTraceEntry(
                source_tag=tag,
                effect="corpus_mitigation",
                weight="low",
                impact_areas=["anti_pattern_corpus"],
                mechanism="auxiliary",
                explanation=(
                    "Resposta positiva do assistente injeta termos de controlo no corpus agregado "
                    "usado pelo matcher de anti-patterns (reduz falsos positivos de `missing_any_of`)."
                ),
            )
        )
    return out


def _build_ranking_trace_entries(
    *,
    admin: bool,
    file_r: bool,
    api_r: bool,
    ecom: bool,
    signals: list[WizardSignal],
) -> list[WizardSignalTraceEntry]:
    trace: list[WizardSignalTraceEntry] = []
    if admin:
        negs = [s for s in signals if s.profile == "internal_admin_portal" and s.value == "no"]
        tag = ",".join(f"wz:{s.profile}:{s.key}=no" for s in negs[:4])
        trace.append(
            WizardSignalTraceEntry(
                source_tag=tag,
                effect="ranking_impact",
                weight="moderate",
                impact_areas=["heuristic_ranking"],
                mechanism="contextual",
                explanation=(
                    "≥2 lacunas admin declaradas (sem mitigador approval=yes): +1 impacto em heurísticas "
                    "admin/privilégio/auditoria (cap 5)."
                ),
            )
        )
    if file_r:
        trace.append(
            WizardSignalTraceEntry(
                source_tag="wz:file_handling_application:cluster",
                effect="ranking_impact",
                weight="moderate",
                impact_areas=["heuristic_ranking"],
                mechanism="contextual",
                explanation=(
                    "Combinação quarentena+scan ausentes ou objetos públicos: +1 impacto em heurísticas de upload/ficheiro."
                ),
            )
        )
    if api_r:
        trace.append(
            WizardSignalTraceEntry(
                source_tag="wz:api_backend_rest:cluster",
                effect="ranking_impact",
                weight="moderate",
                impact_areas=["heuristic_ranking"],
                mechanism="contextual",
                explanation=(
                    "≥2 entre auth/rate/WAF declarados como fracos: +1 impacto em heurísticas de perímetro/API."
                ),
            )
        )
    if ecom:
        trace.append(
            WizardSignalTraceEntry(
                source_tag="wz:industry_ecommerce:cluster",
                effect="ranking_impact",
                weight="moderate",
                impact_areas=["heuristic_ranking"],
                mechanism="contextual",
                explanation=(
                    "≥2 lacunas em checkout/PSP/dados sensíveis: +1 impacto em heurísticas de pagamento."
                ),
            )
        )

    # Observações: sinais negativos isolados que não armaram o cluster
    if _admin_negative_count(signals) == 1 and not admin:
        trace.append(
            WizardSignalTraceEntry(
                source_tag="wz:internal_admin_portal:isolated_no",
                effect="observation",
                weight="low",
                impact_areas=["audit_only"],
                mechanism="auxiliary",
                explanation=(
                    "Uma única resposta negativa no perfil admin não aplica boost de ranking (política anti-overfitting)."
                ),
            )
        )
    if _api_negative_count(signals) == 1 and not api_r:
        trace.append(
            WizardSignalTraceEntry(
                source_tag="wz:api_backend_rest:isolated_no",
                effect="observation",
                weight="low",
                impact_areas=["audit_only"],
                mechanism="auxiliary",
                explanation="Uma única fraqueza API declarada não aplica boost — requer confirmação cruzada (≥2 eixos).",
            )
        )
    mit = _admin_mitigators(signals)
    for s in mit:
        if s.key in ("approval", "segregation", "jit"):
            trace.append(
                WizardSignalTraceEntry(
                    source_tag=f"wz:{s.profile}:{s.key}=yes",
                    effect="observation",
                    weight="low",
                    impact_areas=["mitigation_note"],
                    mechanism="auxiliary",
                    explanation="Mitigador declarado no assistente — documentado para auditoria; pode bloquear boost de ranking.",
                ),
            )
    return trace


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
) -> tuple[int, list[str], list[WizardSignalTraceEntry]]:
    """
    Aumenta impacto (conservador, +1, cap) quando clusters do assistente estão armados.

    Devolve (n_alterados, notas_explicativas, audit_trail).
    """
    sigs = signals_for_profile(doc)
    if not sigs:
        return 0, [], []

    notes: list[str] = []
    admin = _admin_risk_signal(sigs)
    file_r = _file_risk_signal(sigs)
    api_r = _api_risk_signal(sigs)
    ecom = _ecom_risk_signal(sigs)

    trace = _build_ranking_trace_entries(
        admin=admin, file_r=file_r, api_r=api_r, ecom=ecom, signals=sigs
    )

    if admin:
        notes.append(
            "Assistente: ≥2 lacunas admin declaradas (sem mitigador de aprovação) — reforço conservador em achados admin/privilégio."
        )
    if file_r:
        notes.append(
            "Assistente: quarentena+scan ausentes ou exposição pública — reforço em achados de ficheiro/upload."
        )
    if api_r:
        notes.append(
            "Assistente: ≥2 fraquezas API/perímetro declaradas — reforço em achados de perímetro/API."
        )
    if ecom:
        notes.append(
            "Assistente: ≥2 lacunas e-commerce declaradas — reforço em achados de pagamento."
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

    return changed, notes, trace
