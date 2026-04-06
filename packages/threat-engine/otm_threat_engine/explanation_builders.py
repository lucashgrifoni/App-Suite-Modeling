"""
Constrói `ExplanationRecord` a partir do documento e do resultado de análise.
"""

from __future__ import annotations

from otm_core_schema import Asset, ThreatModelDocument
from otm_explainability import (
    ExplanationCategory,
    ExplanationRecord,
    ExplanationType,
    RelatedEntityRef,
    explanation_id,
)

from otm_threat_engine.ai_modeling.explanations import append_plot4ai_merge_explanations
from otm_threat_engine.engine_support import cross_boundary_flow_ids
from otm_threat_engine.result import (
    AnalysisResult,
    HeuristicThreat,
    StructuralFinding,
    TrustBoundaryFinding,
)


def _comp_label(doc: ThreatModelDocument, cid: str | None) -> str | None:
    if not cid:
        return None
    for c in doc.components:
        if c.id == cid:
            return f"{c.name} ({c.id})"
    return cid


def _asset_note(doc: ThreatModelDocument, aid: str | None) -> str | None:
    if not aid:
        return None
    for a in doc.assets:
        if isinstance(a, Asset) and a.id == aid:
            sens = a.sensitivity or "sensibilidade não declarada"
            return f"ativo {a.name} — {sens}"
    return None


def _threat_explanation(
    doc: ThreatModelDocument,
    h: HeuristicThreat,
    *,
    seq: int,
    xb_flows: set[str],
) -> ExplanationRecord:
    score = h.risk.score if h.risk.score is not None else float(h.risk.likelihood * h.risk.impact)
    target = _comp_label(doc, h.target_component_id)
    flow = h.target_data_flow_id
    asset_line = _asset_note(doc, h.target_asset_id)
    ev: list[str] = [
        f"STRIDE {h.stride.value} com score ~{score:.0f} (L={h.risk.likelihood}, I={h.risk.impact}).",
    ]
    if target:
        ev.append(f"Componente alvo: {target}.")
    if flow:
        ev.append(f"Fluxo referido: {flow}.")
        if flow in xb_flows:
            ev.append("Fluxo cruza trust boundaries no diagrama.")
    if asset_line:
        ev.append(asset_line)
    if h.framework_refs:
        ev.append("Normas: " + ", ".join(f"{fr.framework}:{fr.control_id}" for fr in h.framework_refs[:4]))
    msg = (
        f"Heurística identificou {h.stride.value}"
        f"{' em ' + target if target else ''} com base no desenho e no motor STRIDE."
    )
    if flow and flow in xb_flows:
        msg += " O fluxo atravessa fronteira: exposição típica maior."

    rel = [RelatedEntityRef(entity_kind="heuristic_threat", entity_id=h.id)]
    if h.target_component_id:
        rel.append(RelatedEntityRef(entity_kind="component", entity_id=h.target_component_id))
    return ExplanationRecord(
        id=explanation_id(seq, prefix="exp_ht"),
        type=ExplanationType.THREAT_HEURISTIC,
        category=ExplanationCategory.THREAT,
        subject=h.title[:120],
        message=msg,
        evidence=ev,
        confidence="high" if score >= 15 else "medium",
        related_entities=rel,
        reasoning_path=["Heurística STRIDE", "Alvo no diagrama", "Score L×I"],
    )


def _risk_note_for_threat(
    doc: ThreatModelDocument,
    h: HeuristicThreat,
    *,
    seq: int,
    xb_flows: set[str],
) -> ExplanationRecord | None:
    score = h.risk.score if h.risk.score is not None else float(h.risk.likelihood * h.risk.impact)
    flow = h.target_data_flow_id
    boundary_hit = flow in xb_flows if flow else False
    asset_line = _asset_note(doc, h.target_asset_id)

    if score < 12:
        return None
    if not boundary_hit and score < 20:
        if not (asset_line and ("crític" in asset_line.lower() or "restrict" in asset_line.lower())):
            return None

    parts = [f"Score ~{score:.0f} merece prioridade na triagem."]
    if boundary_hit:
        parts.append("Fluxo cruza boundary externa ou entre zonas.")
    if asset_line:
        parts.append(asset_line)
    return ExplanationRecord(
        id=explanation_id(seq, prefix="exp_rk"),
        type=ExplanationType.RISK_SCORE,
        category=ExplanationCategory.RISK,
        subject=f"Prioridade de risco · {h.id}",
        message=" ".join(parts),
        evidence=[f"L×I = {h.risk.likelihood}×{h.risk.impact}", f"Fluxo {flow or '—'}"],
        confidence="medium",
        related_entities=[RelatedEntityRef(entity_kind="heuristic_threat", entity_id=h.id)],
    )


def _structural_exp(sf: StructuralFinding, seq: int) -> ExplanationRecord:
    return ExplanationRecord(
        id=explanation_id(seq, prefix="exp_sf"),
        type=ExplanationType.STRUCTURAL_FINDING,
        category=ExplanationCategory.GOVERNANCE,
        subject=f"Estrutural {sf.code}",
        message="Correção melhora consistência do modelo antes de confiar nas heurísticas.",
        evidence=[sf.message, f"Severidade: {sf.severity}."],
        confidence="high",
        related_entities=[RelatedEntityRef(entity_kind="structural_finding", entity_id=sf.code)],
    )


def _trust_boundary_exp(tf: TrustBoundaryFinding, seq: int) -> ExplanationRecord:
    ev = [tf.message]
    if tf.data_flow_id:
        ev.append(f"Fluxo: {tf.data_flow_id}")
    if tf.from_boundary_id and tf.to_boundary_id:
        ev.append(f"Zonas `{tf.from_boundary_id}` → `{tf.to_boundary_id}`.")
    return ExplanationRecord(
        id=explanation_id(seq, prefix="exp_tb"),
        type=ExplanationType.TRUST_BOUNDARY,
        category=ExplanationCategory.TRUST_BOUNDARY,
        subject=f"Fronteira {tf.code}",
        message=("Tráfego entre perímetros exige controlos explícitos; usar este achado para rever segmentação."),
        evidence=ev,
        confidence="high",
        related_entities=[
            RelatedEntityRef(entity_kind="data_flow", entity_id=tf.data_flow_id or tf.code),
        ],
    )


def merge_analysis_explanations(
    doc: ThreatModelDocument,
    result: AnalysisResult,
    *,
    methodology_explanations: tuple[ExplanationRecord, ...] | None = None,
    recommendation_reason: str | None = None,
) -> list[ExplanationRecord]:
    out: list[ExplanationRecord] = list(methodology_explanations or [])
    seq = len(out)

    if recommendation_reason and not methodology_explanations:
        seq += 1
        out.append(
            ExplanationRecord(
                id=explanation_id(seq),
                type=ExplanationType.METHODOLOGY_RECOMMENDATION,
                category=ExplanationCategory.METHODOLOGY,
                subject="Metodologia (auto)",
                message=recommendation_reason,
                evidence=["Análise com recomendação automática de metodologia."],
                confidence="medium",
                related_entities=[RelatedEntityRef(entity_kind="document", entity_id=doc.metadata.title[:120])],
            )
        )

    seq = len(out)
    xb = cross_boundary_flow_ids(doc)

    for sf in result.structural_findings:
        seq += 1
        out.append(_structural_exp(sf, seq))

    for tf in result.trust_boundary_findings:
        seq += 1
        out.append(_trust_boundary_exp(tf, seq))

    for h in result.heuristic_threats:
        if h.skipped_as_duplicate:
            continue
        seq += 1
        out.append(_threat_explanation(doc, h, seq=seq, xb_flows=xb))
        rk = _risk_note_for_threat(doc, h, seq=seq + 1, xb_flows=xb)
        if rk:
            seq += 1
            out.append(rk.model_copy(update={"id": explanation_id(seq, prefix="exp_rk")}))

    append_plot4ai_merge_explanations(out, doc, result)
    return out
