"""Orquestração da análise: um ponto de entrada claro."""

from __future__ import annotations

from otm_core_schema import StrideCategory, ThreatModelDocument, ThreatModelMethodology
from otm_industry_packs.models import PackDefinition

from otm_threat_engine.pack_runtime import apply_pack_to_li, iter_pack_heuristic_threats
from otm_threat_engine.result import AnalysisResult, AnalysisSummary, HeuristicThreat
from otm_threat_engine.risk_calc import (
    build_risk_assessment,
    likelihood_impact_for_component,
    likelihood_impact_for_data_flow,
)
from otm_threat_engine.stride_heuristics import (
    description_for_component_threat,
    stride_for_cross_boundary_flow,
    strides_for_component,
    strides_for_unencrypted_flow,
    title_for_component_threat,
)
from otm_threat_engine.framework_refs import enrich_analysis_framework_refs
from otm_threat_engine.methodologies import apply_methodology_lens, recommend_methodology
from otm_threat_engine.structural import collect_structural_findings
from otm_threat_engine.trust_insights import analyze_trust_boundary_crossings
from otm_threat_engine.version import ENGINE_VERSION


def _existing_threat_keys(doc: ThreatModelDocument) -> set[tuple[str | None, str | None, str]]:
    keys: set[tuple[str | None, str | None, str]] = set()
    for t in doc.threats:
        keys.add(
            (
                t.target_component_id,
                t.target_data_flow_id,
                t.stride.value,
            )
        )
    return keys


def _cross_boundary_flow_ids(doc: ThreatModelDocument) -> set[str]:
    ids = set()
    by_comp = {c.id: c for c in doc.components}
    for flow in doc.data_flows:
        a = by_comp.get(flow.from_component)
        b = by_comp.get(flow.to_component)
        if not a or not b:
            continue
        if (
            a.in_trust_boundary
            and b.in_trust_boundary
            and a.in_trust_boundary != b.in_trust_boundary
        ):
            ids.add(flow.id)
    return ids


def _recompute_summary_with_methodology(result: AnalysisResult) -> AnalysisResult:
    active = [h for h in result.heuristic_threats if not h.skipped_as_duplicate]
    active_scores = [h.risk.score for h in active if h.risk.score is not None]
    summary = result.summary.model_copy(
        update={
            "heuristic_threats_generated": len(active),
            "heuristic_threats_skipped_duplicate": len(result.heuristic_threats) - len(active),
            "max_risk_score": max(active_scores) if active_scores else None,
        }
    )
    return result.model_copy(update={"summary": summary})


class ThreatAnalysisEngine:
    """
    Motor inicial: validação estrutural (avisos), insights de fronteira,
    ameaças heurísticas STRIDE e pontuação L×I.
    Opcionalmente aplica um industry pack (pesos e ameaças de contexto).
    """

    def _analyze_stride_core(
        self,
        doc: ThreatModelDocument,
        pack: PackDefinition | None = None,
    ) -> AnalysisResult:
        structural = collect_structural_findings(doc)
        trust_findings = analyze_trust_boundary_crossings(doc)
        existing = _existing_threat_keys(doc)
        assets_by_id = {a.id: a for a in doc.assets}
        cross_flows = _cross_boundary_flow_ids(doc)

        heuristics: list[HeuristicThreat] = []
        skipped = 0

        for comp in doc.components:
            for stride in strides_for_component(comp.kind):
                key = (comp.id, None, stride.value)
                raw = likelihood_impact_for_component(comp, stride, assets_by_id=assets_by_id)
                li = apply_pack_to_li(raw[0], raw[1], pack)
                if key in existing:
                    heuristics.append(
                        HeuristicThreat(
                            id=f"eng_{comp.id}_{stride.value}",
                            title=title_for_component_threat(comp, stride),
                            description=description_for_component_threat(comp, stride),
                            stride=stride,
                            target_component_id=comp.id,
                            risk=build_risk_assessment(*li),
                            skipped_as_duplicate=True,
                        )
                    )
                    skipped += 1
                    continue

                heuristics.append(
                    HeuristicThreat(
                        id=f"eng_{comp.id}_{stride.value}",
                        title=title_for_component_threat(comp, stride),
                        description=description_for_component_threat(comp, stride),
                        stride=stride,
                        target_component_id=comp.id,
                        risk=build_risk_assessment(*li),
                        skipped_as_duplicate=False,
                    )
                )

        for flow in doc.data_flows:
            crosses = flow.id in cross_flows
            unencrypted = flow.encrypted is not True

            flow_strides: list[tuple[str, str, str]] = []
            if crosses:
                s = stride_for_cross_boundary_flow()
                flow_strides.append(
                    (
                        s.value,
                        f"Atravessa fronteira — {flow.id}",
                        "Fluxo entre zonas de confiança distintas; rever integridade e "
                        "autenticação de extremidades.",
                    )
                )
            if unencrypted:
                for stride in strides_for_unencrypted_flow():
                    flow_strides.append(
                        (
                            stride.value,
                            f"Canal do fluxo {flow.name or flow.id}",
                            (
                                f"Propriedades de confidencialidade/integridade a rever no fluxo "
                                f"'{flow.id}' ({flow.from_component} → {flow.to_component})."
                            ),
                        )
                    )

            seen_stride: set[str] = set()
            for stride_val, title_short, desc in flow_strides:
                if stride_val in seen_stride:
                    continue
                seen_stride.add(stride_val)

                stride = StrideCategory(stride_val)
                key = (None, flow.id, stride.value)
                hid = f"eng_flow_{flow.id}_{stride.value}"
                raw = likelihood_impact_for_data_flow(
                    flow, crosses_boundary=crosses or unencrypted
                )
                li = apply_pack_to_li(raw[0], raw[1], pack)

                if key in existing:
                    heuristics.append(
                        HeuristicThreat(
                            id=hid,
                            title=f"[{stride.value}] {title_short}",
                            description=desc,
                            stride=stride,
                            target_data_flow_id=flow.id,
                            risk=build_risk_assessment(*li),
                            skipped_as_duplicate=True,
                        )
                    )
                    skipped += 1
                    continue

                heuristics.append(
                    HeuristicThreat(
                        id=hid,
                        title=f"[{stride.value}] {title_short}",
                        description=desc,
                        stride=stride,
                        target_data_flow_id=flow.id,
                        risk=build_risk_assessment(*li),
                        skipped_as_duplicate=False,
                    )
                )

        base_generated = sum(1 for h in heuristics if not h.skipped_as_duplicate)
        covered = set(_existing_threat_keys(doc))
        for h in heuristics:
            if not h.skipped_as_duplicate:
                covered.add(
                    (h.target_component_id, h.target_data_flow_id, h.stride.value),
                )

        pack_gen = 0
        pack_skip = 0
        pack_hints: list[str] = []
        if pack is not None:
            pack_hints = list(pack.control_hints)
            pack_heuristics, pack_skip = iter_pack_heuristic_threats(doc, pack, covered)
            heuristics.extend(pack_heuristics)
            pack_gen = sum(1 for h in pack_heuristics if not h.skipped_as_duplicate)

        active_scores = [
            h.risk.score
            for h in heuristics
            if not h.skipped_as_duplicate and h.risk.score is not None
        ]
        max_score = max(active_scores) if active_scores else None

        summary = AnalysisSummary(
            structural_findings=len(structural),
            trust_boundary_findings=len(trust_findings),
            heuristic_threats_generated=base_generated,
            heuristic_threats_skipped_duplicate=skipped,
            pack_threats_generated=pack_gen,
            pack_threats_skipped_duplicate=pack_skip,
            max_risk_score=max_score,
        )

        raw = AnalysisResult(
            engine_version=ENGINE_VERSION,
            methodology=ThreatModelMethodology.STRIDE,
            document_title=doc.metadata.title,
            structural_findings=structural,
            trust_boundary_findings=trust_findings,
            heuristic_threats=heuristics,
            summary=summary,
            industry_pack_id=pack.id if pack else None,
            pack_control_hints=pack_hints,
        )
        return enrich_analysis_framework_refs(raw)

    def analyze(
        self,
        doc: ThreatModelDocument,
        pack: PackDefinition | None = None,
        *,
        methodology: ThreatModelMethodology | str | None = None,
        auto_recommend: bool = False,
    ) -> AnalysisResult:
        chosen = (
            ThreatModelMethodology(methodology)
            if methodology is not None
            else (doc.model_info.methodology or ThreatModelMethodology.STRIDE)
        )
        rec_reason: str | None = None
        if auto_recommend and methodology is None:
            rec = recommend_methodology(doc)
            chosen = rec.methodology
            rec_reason = rec.reason

        base = self._analyze_stride_core(doc, pack=pack)
        final = apply_methodology_lens(doc, base, methodology=chosen).model_copy(
            update={
                "methodology": chosen,
                "methodology_recommendation_reason": rec_reason,
            }
        )
        final = enrich_analysis_framework_refs(final)
        return _recompute_summary_with_methodology(final)


def analyze_document(
    doc: ThreatModelDocument,
    pack: PackDefinition | None = None,
    *,
    methodology: ThreatModelMethodology | str | None = None,
    auto_recommend: bool = False,
) -> AnalysisResult:
    """Atalho funcional equivalente a `ThreatAnalysisEngine().analyze(...)`."""
    return ThreatAnalysisEngine().analyze(
        doc,
        pack=pack,
        methodology=methodology,
        auto_recommend=auto_recommend,
    )
