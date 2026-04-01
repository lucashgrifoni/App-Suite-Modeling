"""Constrói `RemediationBacklog` a partir de `ThreatModelDocument` + `AnalysisResult`."""

from __future__ import annotations

from collections import defaultdict

from otm_core_schema import ThreatModelMethodology
from otm_core_schema.document import ThreatModelDocument
from otm_explainability import (
    ExplanationCategory,
    ExplanationRecord,
    ExplanationType,
    RelatedEntityRef,
    explanation_id,
)

from otm_threat_engine.remediation.classify import (
    classify_threat,
    effort_for_threat,
    impact_level_from_risk,
)
from otm_threat_engine.remediation.models import (
    BacklogItem,
    FindingRef,
    RemediationBacklog,
)
from otm_threat_engine.result import AnalysisResult, HeuristicThreat


def _risk_score(t: HeuristicThreat) -> float:
    if t.risk.score is not None:
        return float(t.risk.score)
    return float(t.risk.likelihood * t.risk.impact)


def _priority_label(score: float) -> str:
    if score >= 20:
        return "urgent"
    if score >= 15:
        return "high"
    if score >= 9:
        return "medium"
    return "low"


def _owner_for(layer: str | None, category: str, ctrl: str) -> tuple[str | None, str]:
    if category == "third_party_integration":
        return "vendor_or_integration_lead", "Integração/envolvendo terceiros no modelo."
    if category == "ai_ml_specific":
        return "ml_platform_or_app_security", "Metodologia ou texto indicam risco ML/LLM."
    if layer == "edge":
        return "platform_engineering", "Componente na borda (gateway/externo) tende a equipa de plataforma."
    if layer == "data":
        return "data_owner_and_engineering", "Ativo ou armazém — dono de dados + engenharia."
    if layer == "application":
        return "application_team", "Processo de aplicação no centro do achado."
    if category == "observability_audit":
        return "platform_or_sre", "Logs, auditoria e resiliência envolvem frequentemente SRE/plataforma."
    if ctrl == "identity_access":
        return "identity_security_champions", "Autenticação/autorização — tipicamente IdP + app."
    return None, "Perfil de owner não inferido com confiança — atribuir no processo interno."


def _item_from_threat(
    threat: HeuristicThreat,
    doc: ThreatModelDocument | None,
    methodology: ThreatModelMethodology,
    seq: int,
    exp_seq_ref: list[int],
) -> BacklogItem:
    rid, ctrl, cat, layer = classify_threat(threat, doc, methodology)
    effort = effort_for_threat(threat, rid)
    impact = impact_level_from_risk(threat)
    score = _risk_score(threat)
    plab = _priority_label(score)
    urgent = plab == "urgent"

    comps: list[str] = []
    labels: list[str] = []
    if threat.target_component_id:
        comps.append(threat.target_component_id)
    if doc:
        by_id = {c.id: c.name for c in doc.components}
        labels = [by_id[c] for c in comps if c in by_id]

    owner, owner_expl = _owner_for(layer, cat, ctrl)

    qw = effort == "low" and (impact == "high" or score >= 12)
    foundational = ctrl == "identity_access" and score >= 9

    title = f"Mitigar: {threat.title[:80]}"
    desc = (
        f"Endereçar o achado '{threat.id}' ({threat.stride.value}). "
        f"Controlo sugerido: {ctrl.replace('_', ' ')}."
    )
    rationale = (
        f"Derivado da ameaça heurística {threat.id} (STRIDE {threat.stride.value}) "
        f"com score de risco ~{score:.0f}."
    )
    pexpl = (
        f"Etiqueta '{plab}' por heurística L×I (ou score agregado): valor ~{score:.0f}. "
        "Não substitui avaliação de risco do negócio."
    )
    qw_expl = (
        "Marcado como quick win porque o esforço estimado é baixo e o impacto ou score são elevados."
        if qw
        else "Não classificado como quick win com base em esforço/impacto heurísticos."
    )
    fo_expl = (
        "Marcado como foundational porque reforço de identidade/acesso reduz múltiplas classes STRIDE."
        if foundational
        else "Não marcado como foundational neste conjunto."
    )

    next_step = (
        f"Rever o componente alvo e aplicar controlos alinhados a '{ctrl}'; "
        f"validar com equipa ({owner or 'owner a definir'})."
    )

    explain = [
        f"Cobre o achado heurístico `{threat.id}`.",
        pexpl,
        f"Causa raiz agrupada: `{rid}`; categoria `{cat}`.",
        "Limitação: mapeamento STRIDE→controlo é genérico; adaptar ao vosso catálogo interno.",
    ]

    def take_exp() -> int:
        exp_seq_ref[0] += 1
        return exp_seq_ref[0]

    bl_explanations: list[ExplanationRecord] = [
        ExplanationRecord(
            id=explanation_id(take_exp(), prefix="exp_bl"),
            type=ExplanationType.BACKLOG_PRIORITIZATION,
            category=ExplanationCategory.BACKLOG,
            subject=f"Ação · {threat.id}"[:200],
            message=(
                f"Item criado a partir da heurística `{threat.id}` (STRIDE {threat.stride.value}) "
                f"com score ~{score:.0f}; controlo sugerido `{ctrl}` na categoria `{cat}`."
            ),
            evidence=[rationale, pexpl],
            confidence="medium",
            related_entities=[RelatedEntityRef(entity_kind="heuristic_threat", entity_id=threat.id)],
        )
    ]
    if qw:
        bl_explanations.append(
            ExplanationRecord(
                id=explanation_id(take_exp(), prefix="exp_bl"),
                type=ExplanationType.BACKLOG_PRIORITIZATION,
                category=ExplanationCategory.BACKLOG,
                subject="Quick win",
                message=(
                    "Ação priorizada como quick win neste lote: esforço estimado baixo e "
                    "impacto ou score elevados neste achado."
                ),
                evidence=[qw_expl],
                confidence="low",
                related_entities=[RelatedEntityRef(entity_kind="heuristic_threat", entity_id=threat.id)],
            )
        )

    return BacklogItem(
        id=f"bl_ht_{threat.id}_{seq:03d}",
        title=title,
        description=desc,
        rationale=rationale,
        related_findings=[FindingRef(kind="heuristic_threat", id=threat.id)],
        related_components=comps,
        component_labels=labels,
        methodology_context=methodology.value,
        suggested_control_type=ctrl,
        control_category=cat,
        grouped_root_cause=rid,
        architecture_layer=layer,
        priority_rank=1,
        priority_label=plab,  # type: ignore[arg-type]
        priority_explanation=pexpl,
        effort_estimate=effort,  # type: ignore[arg-type]
        impact_estimate=impact,  # type: ignore[arg-type]
        recommended_owner=owner,
        owner_explanation=owner_expl,
        quick_win=qw,
        foundational=foundational,
        urgent=urgent,
        quick_win_explanation=qw_expl,
        foundational_explanation=fo_expl,
        next_step=next_step,
        depends_on_action_ids=[],
        explainability=explain,
        explanations=bl_explanations,
    )


def _item_from_structural(
    code: str,
    message: str,
    seq: int,
    exp_seq_ref: list[int],
) -> BacklogItem:
    exp_seq_ref[0] += 1
    exps = [
        ExplanationRecord(
            id=explanation_id(exp_seq_ref[0], prefix="exp_bl"),
            type=ExplanationType.BACKLOG_PRIORITIZATION,
            category=ExplanationCategory.BACKLOG,
            subject=f"Backlog · {code}"[:200],
            message=(
                f"Acção derivada do achado estrutural `{code}` para saneamento do modelo "
                "antes de confiar nas heurísticas."
            ),
            evidence=[message],
            confidence="high",
            related_entities=[RelatedEntityRef(entity_kind="structural_finding", entity_id=code)],
        )
    ]
    return BacklogItem(
        id=f"bl_sf_{code}_{seq:03d}",
        title=f"Corrigir modelo: {code}",
        description=message,
        rationale="Achado estrutural do motor — o diagrama ou metadados podem prejudicar análises futuras.",
        related_findings=[FindingRef(kind="structural", id=code)],
        suggested_control_type="model_governance",
        control_category="governance",
        grouped_root_cause="threat_model_hygiene",
        architecture_layer="governance",
        priority_rank=1,
        priority_label="medium",
        priority_explanation=(
            "Prioridade média por defeito: consistência do modelo habilita análise fiável."
        ),
        effort_estimate="low",
        impact_estimate="medium",
        recommended_owner="security_architecture",
        owner_explanation="Quem mantém o threat model as-code costuma ser arquitetura ou AppSec.",
        quick_win=True,
        foundational=False,
        urgent=False,
        quick_win_explanation="Ajustes estruturais costumam ser localizados no YAML/diagrama.",
        foundational_explanation="Não é controlo foundational de infra — é higiene do artefacto.",
        next_step="Actualizar o documento canónico para resolver o código estrutural indicado.",
        explainability=[
            f"Fonte: structural finding `{code}`.",
            "Resolver melhora rastreabilidade entre componentes e fluxos.",
        ],
        explanations=exps,
    )


def _item_from_trust_boundary(
    code: str,
    message: str,
    seq: int,
    flow_id: str | None,
    exp_seq_ref: list[int],
) -> BacklogItem:
    fid = flow_id or "unknown_flow"
    exp_seq_ref[0] += 1
    exps = [
        ExplanationRecord(
            id=explanation_id(exp_seq_ref[0], prefix="exp_bl"),
            type=ExplanationType.BACKLOG_PRIORITIZATION,
            category=ExplanationCategory.BACKLOG,
            subject=f"Fronteira · {code}"[:200],
            message=(
                f"Item ligado ao cruzamento de trust boundary `{code}` no fluxo `{fid}`; "
                "prioridade alta por exposição entre perímetros."
            ),
            evidence=[message],
            confidence="high",
            related_entities=[
                RelatedEntityRef(entity_kind="trust_boundary_finding", entity_id=f"{code}:{fid}"),
            ],
        )
    ]
    return BacklogItem(
        id=f"bl_tb_{code}_{seq:03d}",
        title=f"Fronteira de confiança: {code}",
        description=message,
        rationale="Fluxo ou fronteira mal definidos aumentam superfície de ataque cruzando perímetros.",
        related_findings=[FindingRef(kind="trust_boundary", id=f"{code}:{fid}")],
        related_components=[],
        suggested_control_type="segmentation_and_encryption",
        control_category="surface_exposure",
        grouped_root_cause="trust_perimeter_crossing",
        architecture_layer="edge",
        priority_rank=1,
        priority_label="high",
        priority_explanation=(
            "Prioridade alta heurística: tráfego entre fronteiras sem clareza é risco sistémico comum."
        ),
        effort_estimate="medium",
        impact_estimate="high",
        recommended_owner="platform_engineering",
        owner_explanation="Controlo de rede/segmentação costuma cair em plataforma ou cloud centre of excellence.",
        quick_win=False,
        foundational=True,
        urgent=False,
        quick_win_explanation="Normalmente exige desenho de rede ou cifragem — não é quick win automático.",
        foundational_explanation="Segmentação correcta é base para outros controlos.",
        next_step="Rever fluxo em questão, cifragem, políticas de ingress/egress e zonas de confiança.",
        explainability=[
            f"Fonte: trust boundary finding `{code}` (fluxo `{fid}`).",
            "Confirmar se o fluxo deve mesmo atravessar o perímetro e documentar controlos.",
        ],
        explanations=exps,
    )


def _item_from_pack_hint(hint: str, seq: int, exp_seq_ref: list[int]) -> BacklogItem:
    short = hint[:60] + ("…" if len(hint) > 60 else "")
    exp_seq_ref[0] += 1
    exps = [
        ExplanationRecord(
            id=explanation_id(exp_seq_ref[0], prefix="exp_bl"),
            type=ExplanationType.CONTROL_SUGGESTION,
            category=ExplanationCategory.CONTROL,
            subject=f"Pack · {short}"[:200],
            message="Sugestão propagada a partir de `pack_control_hints` após correção do motor com industry pack.",
            evidence=[hint[:400]],
            confidence="medium",
            related_entities=[RelatedEntityRef(entity_kind="pack_hint", entity_id=f"pack_hint_{seq}")],
        )
    ]
    return BacklogItem(
        id=f"bl_pk_{seq:03d}",
        title=f"Pack / controlo: {short}",
        description=hint,
        rationale="Sugestão do industry pack após análise — pode mapear para controlos de compliance.",
        related_findings=[FindingRef(kind="pack_hint", id=f"pack_hint_{seq}")],
        suggested_control_type="compliance_and_pack_control",
        control_category="cross_cutting",
        grouped_root_cause="industry_pack_recommendation",
        architecture_layer=None,
        priority_rank=1,
        priority_label="medium",
        priority_explanation="Prioridade média: relevância depende do programa de compliance activo.",
        effort_estimate="medium",
        impact_estimate="medium",
        recommended_owner=None,
        owner_explanation="Owner depende do catálogo (GRC, AppSec, produto) — não inferido automaticamente.",
        quick_win=False,
        foundational=False,
        urgent=False,
        quick_win_explanation="Implementação de controlos de pack raramente é trivial.",
        foundational_explanation="Pode tornar-se foundational se obrigatório regulatório.",
        next_step="Cruzar com o program de controlos internos e abrir iniciativa se aplicável.",
        explainability=[
            "Origem: `pack_control_hints` do resultado de análise.",
            "Validar com dono do pack/compliance antes de comprometer roadmap.",
        ],
        explanations=exps,
    )


def build_remediation_backlog(
    result: AnalysisResult,
    doc: ThreatModelDocument | None = None,
) -> RemediationBacklog:
    """
    Gera backlog a partir da análise. O documento é opcional mas melhora nomes e camadas.
    """
    items: list[BacklogItem] = []
    n = 0
    exp_seq_ref = [0]

    for t in result.heuristic_threats:
        if t.skipped_as_duplicate:
            continue
        n += 1
        items.append(_item_from_threat(t, doc, result.methodology, n, exp_seq_ref))

    for i, sf in enumerate(result.structural_findings):
        items.append(_item_from_structural(sf.code, sf.message, i, exp_seq_ref))

    for i, tf in enumerate(result.trust_boundary_findings):
        items.append(_item_from_trust_boundary(tf.code, tf.message, i, tf.data_flow_id, exp_seq_ref))

    for i, hint in enumerate(result.pack_control_hints):
        items.append(_item_from_pack_hint(hint, i, exp_seq_ref))

    if not items:
        return RemediationBacklog(
            document_title=result.document_title,
            methodology=result.methodology.value,
            executive_summary="Sem achados accionáveis neste resultado — modelo possivelmente limpo ou análise vazia.",
            synergy_notes=[],
            items=[],
            top_5_action_ids=[],
        )

    def _sort_score(it: BacklogItem) -> float:
        if it.related_findings and it.related_findings[0].kind == "heuristic_threat":
            hid = it.related_findings[0].id
            ht = next((h for h in result.heuristic_threats if h.id == hid), None)
            return _risk_score(ht) if ht else 0.0
        return {"urgent": 22.0, "high": 16.0, "medium": 10.0, "low": 5.0}[it.priority_label]

    order = sorted(range(len(items)), key=lambda i: (-_sort_score(items[i]), items[i].id))
    for rank, idx in enumerate(order, start=1):
        items[idx].priority_rank = rank

    by_root: dict[str, list[str]] = defaultdict(list)
    by_ctrl: dict[str, list[str]] = defaultdict(list)
    by_cat: dict[str, list[str]] = defaultdict(list)
    for it in items:
        by_root[it.grouped_root_cause].append(it.id)
        by_ctrl[it.suggested_control_type].append(it.id)
        by_cat[it.control_category].append(it.id)

    qw = [it.id for it in items if it.quick_win]
    fo = [it.id for it in items if it.foundational]
    himp = [it.id for it in items if it.impact_estimate == "high"]
    heff = [it.id for it in items if it.effort_estimate == "high"]

    synergy: list[str] = []
    for root, ids in by_root.items():
        if len(ids) >= 3:
            synergy.append(
                f"{len(ids)} itens partilham causa raiz `{root}` — avaliar iniciativa única antes de esgotar várias pistas."
            )
    for cat, ids in by_cat.items():
        if cat == "identity_access" and len(ids) >= 2:
            synergy.append(
                f"Vários achados ({len(ids)}) em identidade/acesso — um programa IAM unificado pode reduzir risco agregado."
            )

    auth_items = [it for it in items if it.suggested_control_type == "identity_access"]
    auth_id = auth_items[0].id if auth_items else None
    if auth_id:
        for it in items:
            if it.id == auth_id:
                continue
            if it.control_category == "data" and it.effort_estimate != "low":
                deps = list(it.depends_on_action_ids)
                if auth_id not in deps:
                    deps.append(auth_id)
                it.depends_on_action_ids = deps

    top5 = [it.id for it in sorted(items, key=lambda x: x.priority_rank)[:5]]

    summary = (
        f"{len(items)} acções sugeridas para `{result.document_title}` "
        f"({result.methodology.value}). "
        f"{len(qw)} quick wins; {len(fo)} foundational; {len(himp)} alto impacto estimado."
    )
    return RemediationBacklog(
        document_title=result.document_title,
        methodology=result.methodology.value,
        executive_summary=summary,
        synergy_notes=synergy,
        items=items,
        by_root_cause=dict(by_root),
        by_control_type=dict(by_ctrl),
        by_control_category=dict(by_cat),
        quick_win_ids=qw,
        foundational_ids=fo,
        high_impact_ids=himp,
        high_effort_ids=heff,
        top_5_action_ids=top5,
    )
