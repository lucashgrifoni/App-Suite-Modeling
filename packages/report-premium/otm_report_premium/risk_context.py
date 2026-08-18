"""Heurísticas de exploitability e impacto de negócio — transparentes e não normativas."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from otm_core_schema import ComponentKind, StrideCategory
from otm_core_schema.document import ThreatModelDocument
from otm_threat_engine.remediation.classify import ComponentIndex, component_kind_for_id
from otm_threat_engine.result import HeuristicThreat

from .models import BusinessImpactRow, ExploitabilityProfile


def _blob(threat: HeuristicThreat) -> str:
    return f"{threat.title} {threat.description}".lower()


@dataclass(frozen=True)
class _ExploitSignals:
    remoteish: bool
    requires_mitm: bool
    webhook: bool
    integration: bool
    agent: bool
    prompt: bool
    misconfig: bool


def _exploit_signals(text: str, *, ext: bool, userish: bool) -> _ExploitSignals:
    """Sinais textuais de exploração (heurística por keyword)."""
    return _ExploitSignals(
        remoteish=ext or userish or "api" in text or "extern" in text,
        requires_mitm="mitm" in text or "man-in-the-middle" in text,
        webhook="webhook" in text or "callback" in text or "deep link" in text,
        integration="integra" in text or "third" in text or "terceiro" in text,
        agent="agent" in text or "tool" in text or "função" in text,
        prompt="prompt" in text or "rag" in text or "retrieval" in text or "embedding" in text,
        misconfig="misconfig" in text or "configuração" in text or "expost" in text,
    )


def _infer_locality(
    ck: ComponentKind | None, *, remoteish: bool, userish: bool
) -> Literal["local", "remote", "hybrid", "unknown"]:
    if remoteish and not userish:
        return "remote"
    if ck == ComponentKind.PROCESS and not remoteish:
        return "local"
    if remoteish and userish:
        return "hybrid"
    return "unknown"


def infer_exploitability(
    threat: HeuristicThreat,
    doc: ThreatModelDocument | None,
    *,
    index: ComponentIndex | None = None,
) -> ExploitabilityProfile:
    """
    Infere contexto de exploração com base em STRIDE, alvo e texto — heurística.

    `index` evita reconstruir o mapa de componentes por ameaça (ver `ComponentIndex`).
    """
    ck = component_kind_for_id(doc, threat.target_component_id, index=index)
    text = _blob(threat)

    ext = ck in (ComponentKind.EXTERNAL_ENTITY, ComponentKind.GATEWAY)
    userish = ck == ComponentKind.USER
    sig = _exploit_signals(text, ext=ext, userish=userish)
    locality = _infer_locality(ck, remoteish=sig.remoteish, userish=userish)

    notes_parts: list[str] = []
    if ext:
        notes_parts.append("Superfície externa/gateway tende a exposição remota.")
    if userish:
        notes_parts.append("Envolve utilizador — pode exigir interação ou sessão autenticada.")
    if not notes_parts:
        notes_parts.append("Inferência limitada ao texto e tipo de componente.")

    return ExploitabilityProfile(
        threat_id=threat.id,
        requires_external_access=bool(ext or sig.remoteish),
        requires_authenticated_user=None if not userish else True,
        requires_user_interaction=True if userish else None,
        requires_external_integration_control=True if sig.integration else None,
        requires_mitm=True if sig.requires_mitm else None,
        requires_webhook_or_deeplink=True if sig.webhook else None,
        attack_locality=locality,
        depends_on_agent_tool_use=True if sig.agent else None,
        depends_on_prompt_or_retrieval_abuse=True if sig.prompt else None,
        depends_on_misconfiguration=True if sig.misconfig else None,
        notes=" ".join(notes_parts),
    )


def business_labels_for_stride(threat: HeuristicThreat) -> list[str]:
    """Mapeia STRIDE para etiquetas de impacto de negócio genéricas."""
    mapping: dict[StrideCategory, list[str]] = {
        StrideCategory.SPOOFING: ["account_takeover", "fraud", "accesso_indevido"],
        StrideCategory.TAMPERING: ["integridade_de_dados", "compliance", "risco_operacional"],
        StrideCategory.REPUDIATION: ["perda_de_rastreabilidade", "compliance", "fraude"],
        StrideCategory.INFORMATION_DISCLOSURE: [
            "vazamento_de_dados",
            "risco_de_privacidade",
            "compliance",
        ],
        StrideCategory.DENIAL_OF_SERVICE: ["indisponibilidade", "risco_operacional"],
        StrideCategory.ELEVATION_OF_PRIVILEGE: [
            "movimentacao_lateral",
            "accesso_indevido",
            "abuso_de_integracao",
        ],
    }
    labels = list(mapping.get(threat.stride, ["risco_operacional"]))
    return labels[:5]


def build_business_impact_row(threat: HeuristicThreat) -> BusinessImpactRow:
    labels = business_labels_for_stride(threat)
    rationale = (
        f"Etiquetas derivadas da categoria STRIDE `{threat.stride.value}`; "
        "validar com dono de negócio e contexto regulatório."
    )
    return BusinessImpactRow(threat_id=threat.id, labels=labels, rationale=rationale)


def ai_business_labels_if_applicable(threat: HeuristicThreat) -> list[str]:
    t = _blob(threat)
    extra: list[str] = []
    if any(k in t for k in ("llm", "prompt", "rag", "embedding", "vector")):
        extra.extend(
            [
                "ai_llm_leakage_risk",
                "provider_dependency",
                "groundedness_failure",
            ]
        )
    return extra
