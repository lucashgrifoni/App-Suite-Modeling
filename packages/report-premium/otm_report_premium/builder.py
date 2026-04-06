"""
Constrói `PremiumReportPayload` a partir do documento canónico, análise, backlog e diff opcional.

Toda a lógica pesada de negócio permanece no motor e no backlog; aqui apenas agregamos vistas.
"""

from __future__ import annotations

import importlib.metadata
from collections import Counter, defaultdict
from datetime import date

from otm_core_schema import ComponentKind
from otm_core_schema.document import ThreatModelDocument
from otm_diagram_engine import export_flowchart_mermaid
from otm_threat_engine import build_remediation_backlog
from otm_threat_engine.analysis_diff import diff_analysis_results
from otm_threat_engine.semantic_comparison import semantic_diff_from_analyses_only
from otm_threat_engine.methodologies import recommend_methodology
from otm_threat_engine.result import AnalysisResult, HeuristicThreat

from .dedupe import build_dedupe_groups
from .enums import ReportLevel
from .methodology import methodology_voice_lines
from .models import (
    ArchitectureSummary,
    BaselineDiffSection,
    CoverPage,
    DedupeGroup,
    DistributionBlock,
    ExecutiveSummaryBlock,
    ExplainabilitySnippet,
    GuidedModelingAuditBlock,
    InferenceDisclaimer,
    OwnershipRow,
    PremiumReportPayload,
    QuickWinItem,
    RoadmapPhase,
    RootCauseGroup,
    StrategicRecommendation,
    TechnicalAppendix,
    TopRiskItem,
)
from .prioritize import assign_priority_tier, composite_priority_score, horizon_for_tier
from .risk_context import (
    ai_business_labels_if_applicable,
    build_business_impact_row,
    infer_exploitability,
)

ROOT_CAUSE_LABELS: dict[str, str] = {
    "identity_and_authorization_gaps": "Autenticação / autorização",
    "data_exposure_and_classification": "Dados sensíveis sem proteção suficiente",
    "integrity_and_supply_chain": "Integridade / cadeia de fornecimento",
    "availability_and_resilience": "Disponibilidade e resiliência",
    "non_repudiation_and_audit": "Não repúdio e auditoria",
    "third_party_trust": "Integrações third-party",
    "ai_governance_and_model_risk": "Governança e risco de modelo (AI/LLM)",
    "general_mitigation": "Mitigação geral",
    "trust_perimeter_crossing": "Cruzamento de trust boundary",
    "threat_model_hygiene": "Higiene do artefacto de threat model",
    "industry_pack_recommendation": "Recomendações do industry pack",
}


def _app_version() -> str:
    try:
        return importlib.metadata.version("open-threat-model")
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _severity_band(t: HeuristicThreat) -> str:
    raw = t.risk.score if t.risk.score is not None else float(t.risk.likelihood * t.risk.impact)
    if raw >= 20:
        return "critical"
    if raw >= 15:
        return "high"
    if raw >= 9:
        return "medium"
    return "low"


def _overall_status(max_score: float | None) -> tuple[str, str]:
    if max_score is None:
        return "acceptable_with_follow_up", "Aceitável com acompanhamento (sem score agregado)"
    if max_score >= 20:
        return "requires_immediate_attention", "Requer atenção imediata"
    if max_score >= 12:
        return "action_recommended", "Acção recomendada"
    return "acceptable_with_follow_up", "Aceitável com acompanhamento"


def _risk_label(max_score: float | None) -> str:
    if max_score is None:
        return "não calculado"
    if max_score >= 20:
        return "elevado"
    if max_score >= 15:
        return "alto"
    if max_score >= 9:
        return "médio"
    return "baixo a moderado"


def _component_name(doc: ThreatModelDocument, cid: str | None) -> str | None:
    if not cid:
        return None
    for c in doc.components:
        if c.id == cid:
            return c.name
    return cid


def _asset_name(doc: ThreatModelDocument, aid: str | None) -> str | None:
    if not aid:
        return None
    for a in doc.assets:
        if a.id == aid:
            return a.name
    return aid


def _boundary_name(doc: ThreatModelDocument, bid: str | None) -> str | None:
    if not bid:
        return None
    for b in doc.trust_boundaries:
        if b.id == bid:
            return b.name
    return bid


def build_premium_report_payload(
    doc: ThreatModelDocument,
    result: AnalysisResult,
    *,
    level: ReportLevel,
    baseline: AnalysisResult | None = None,
    app_version: str | None = None,
    include_mermaid: bool = True,
) -> PremiumReportPayload:
    """
    Constrói o payload premium. `baseline` opcional alimenta secção de diff/trend.
    """
    meth = result.methodology
    active: list[HeuristicThreat] = [h for h in result.heuristic_threats if not h.skipped_as_duplicate]
    backlog = build_remediation_backlog(result, doc)
    recommendation = recommend_methodology(doc)
    app_v = app_version or _app_version()

    max_score = result.summary.max_risk_score
    status_key, status_display = _overall_status(max_score)

    comp_names = {c.id: c.name for c in doc.components}
    tb_by_component: dict[str, str] = {}
    for c in doc.components:
        if c.in_trust_boundary:
            tb_by_component[c.id] = c.in_trust_boundary

    # Distribuições
    sev_counter: Counter[str] = Counter()
    stride_counter: Counter[str] = Counter()
    comp_counter: Counter[str] = Counter()
    tb_counter: Counter[str] = Counter()
    heatmap: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for t in active:
        band = _severity_band(t)
        sev_counter[band] += 1
        stride_counter[t.stride.value] += 1
        if t.target_component_id:
            comp_counter[t.target_component_id] += 1
            tb_id = tb_by_component.get(t.target_component_id)
            if tb_id:
                tb_counter[tb_id] += 1
        heatmap[t.stride.value][band] += 1

    for threat in doc.threats:
        stride_counter[threat.stride.value] += 1
        if threat.risk:
            raw = threat.risk.score or float(threat.risk.likelihood * threat.risk.impact)
            band = (
                "critical"
                if raw >= 20
                else "high"
                if raw >= 15
                else "medium"
                if raw >= 9
                else "low"
            )
            sev_counter[band] += 1
        if threat.target_component_id:
            comp_counter[threat.target_component_id] += 1

    methodology_dist = {meth.value: len(active) + len(doc.threats)}
    total_threats = len(active) + len(doc.threats)

    top_boundaries = [
        _boundary_name(doc, bid) or bid
        for bid, _n in tb_counter.most_common(5)
    ]
    top_surfaces = [comp_names.get(cid, cid) for cid, _n in comp_counter.most_common(5)]

    sorted_threats = sorted(
        active,
        key=lambda x: composite_priority_score(x, doc, meth),
        reverse=True,
    )
    top5_titles = [t.title for t in sorted_threats[:5]]

    urgency: str = "high" if (max_score or 0) >= 15 else "medium" if (max_score or 0) >= 9 else "low"

    readiness = [
        "O modelo indica risco elevado à luz das heurísticas actuais?"
        if (max_score or 0) >= 15
        else "Os scores são moderados — validar com testes e contexto de negócio.",
        "O sistema parece pronto para release com estes achados em aberto?",
        "Existem controlos compensatórios ou aceitação formal de risco documentada?",
    ]

    exec_conclusion = (
        f"Foram identificadas {total_threats} ameaças (canónicas + heurísticas activas). "
        f"O score máximo observado é {_risk_label(max_score)}. "
        "Esta conclusão é heurística e não substitui testes de segurança ou auditoria."
    )

    arch_narrative_parts: list[str] = []
    if doc.business_context and doc.business_context.description:
        arch_narrative_parts.append(doc.business_context.description)
    arch_narrative_parts.append(
        f"Componentes: {len(doc.components)} · Fluxos: {len(doc.data_flows)} · "
        f"Fronteiras: {len(doc.trust_boundaries)}."
    )
    arch = ArchitectureSummary(
        narrative=" ".join(arch_narrative_parts),
        main_components=[c.name for c in doc.components[:12]],
        main_flows=[f.name or f.id for f in doc.data_flows[:12]],
        trust_boundaries=[b.name for b in doc.trust_boundaries],
        external_dependencies=[
            c.name for c in doc.components if c.kind == ComponentKind.EXTERNAL_ENTITY
        ][:10],
        sensitive_assets=[
            a.name
            for a in doc.assets
            if (a.sensitivity or "").lower() in ("confidential", "restricted", "high")
        ][:10],
        methodology_used=meth.value,
        methodology_recommended=recommendation.methodology.value,
        recommendation_reason=recommendation.reason,
        mermaid_flowchart=export_flowchart_mermaid(doc) if include_mermaid and level == ReportLevel.DEEP else None,
    )

    # Rankings
    comp_scores: dict[str, float] = defaultdict(float)
    for t in active:
        if t.target_component_id:
            comp_scores[t.target_component_id] += composite_priority_score(t, doc, meth)
    tb_scores: dict[str, float] = defaultdict(float)
    for cid, sc in comp_scores.items():
        bid = tb_by_component.get(cid)
        if bid:
            tb_scores[bid] += sc
    top_comp_ranked = sorted(comp_scores.items(), key=lambda x: -x[1])[:10]
    top_tb_ranked = sorted(tb_scores.items(), key=lambda x: -x[1])[:10]

    distributions = DistributionBlock(
        total_threats=total_threats,
        by_severity_band=dict(sev_counter),
        by_stride=dict(stride_counter),
        by_methodology_tag=methodology_dist,
        by_component={comp_names.get(k, k): v for k, v in comp_counter.most_common(15)},
        by_trust_boundary={
            _boundary_name(doc, k) or k: v for k, v in tb_counter.most_common(15)
        },
        by_risk_type=dict(stride_counter),
        by_control_domain=dict(Counter(b.control_category for b in backlog.items)),
        heatmap_stride_severity={sk: dict(sv) for sk, sv in heatmap.items()},
        top_components_ranked=[(comp_names.get(c, c), s) for c, s in top_comp_ranked],
        top_boundaries_ranked=[(_boundary_name(doc, b) or b, s) for b, s in top_tb_ranked],
    )

    # Top 10
    top_risks: list[TopRiskItem] = []
    for i, t in enumerate(sorted_threats[:10]):
        tier = assign_priority_tier(i, min(10, len(sorted_threats)))
        ex = infer_exploitability(t, doc)
        bi_labels = build_business_impact_row(t).labels + ai_business_labels_if_applicable(t)
        backlog_match = next(
            (b for b in backlog.items if any(r.id == t.id for r in b.related_findings if r.kind == "heuristic_threat")),
            None,
        )
        action = backlog_match.next_step if backlog_match else f"Tratar ameaça `{t.id}` conforme controlos sugeridos."
        top_risks.append(
            TopRiskItem(
                rank=i + 1,
                threat_id=t.id,
                title=t.title,
                methodology=meth.value,
                component=_component_name(doc, t.target_component_id),
                asset=_asset_name(doc, t.target_asset_id),
                severity_score=t.risk.score,
                likelihood=t.risk.likelihood,
                impact=t.risk.impact,
                exploitability_summary=ex.notes,
                business_impact_labels=list(dict.fromkeys(bi_labels))[:8],
                priority_tier=tier,
                composite_score=composite_priority_score(t, doc, meth),
                recommended_action=action,
                suggested_horizon=horizon_for_tier(tier),
            )
        )

    # Root cause groups
    rc_groups: list[RootCauseGroup] = []
    for root_key, item_ids in backlog.by_root_cause.items():
        items = [i for i in backlog.items if i.id in item_ids]
        if not items:
            continue
        comps: set[str] = set()
        for it in items:
            comps.update(it.related_components)
        controls = list({it.suggested_control_type for it in items})[:6]
        rc_groups.append(
            RootCauseGroup(
                key=root_key,
                display_name=ROOT_CAUSE_LABELS.get(root_key, root_key.replace("_", " ").title()),
                threat_count=len(items),
                component_ids=sorted(comps)[:20],
                suggested_controls=controls,
                single_fix_recommendation=items[0].rationale[:500] if items else "",
            )
        )
    rc_groups.sort(key=lambda x: -x.threat_count)

    exploit_profiles = [infer_exploitability(t, doc) for t in sorted_threats[:15]]
    business_rows = [build_business_impact_row(t) for t in sorted_threats[:15]]

    quick_wins: list[QuickWinItem] = []
    for qid in backlog.quick_win_ids[:15]:
        item = next((i for i in backlog.items if i.id == qid), None)
        if not item:
            continue
        quick_wins.append(
            QuickWinItem(
                backlog_item_id=qid,
                title=item.title,
                rationale=item.quick_win_explanation or item.rationale,
            )
        )

    ownership_rows: list[OwnershipRow] = []
    owner_buckets: dict[str, list[str]] = defaultdict(list)
    for it in backlog.items:
        role = it.recommended_owner or "a_definir"
        owner_buckets[role].append(it.id)
    for role, ids in sorted(owner_buckets.items(), key=lambda x: -len(x[1])):
        ownership_rows.append(
            OwnershipRow(
                scope=f"Itens sugeridos para `{role}`",
                suggested_owner_role=None if role == "a_definir" else role,
                explanation="Owner sugerido pelo motor — validar com a governança interna.",
                backlog_item_ids=ids[:30],
            )
        )

    strategic: list[StrategicRecommendation] = [
        StrategicRecommendation(
            title="Baseline de secure architecture",
            detail="Documentar padrões de fronteiras, identidade e dados sensíveis alinhados ao vosso catálogo.",
        ),
        StrategicRecommendation(
            title="Política de integrações",
            detail="Definir requisitos mínimos para webhooks, callbacks e integrações third-party.",
        ),
    ]
    for hint in result.pack_control_hints[:5]:
        strategic.append(
            StrategicRecommendation(title="Pack / controlo", detail=hint[:400]),
        )

    immediate: list[str] = []
    short_term: list[str] = []
    medium: list[str] = []
    for it in sorted(backlog.items, key=lambda x: x.priority_rank):
        line = f"{it.title} ({it.priority_label})"
        if it.urgent or it.priority_label == "urgent":
            immediate.append(line)
        elif it.priority_label in ("high",):
            short_term.append(line)
        else:
            medium.append(line)

    roadmap = [
        RoadmapPhase(phase="immediate", title="Imediato", items=immediate[:12]),
        RoadmapPhase(phase="short", title="Curto prazo", items=short_term[:12]),
        RoadmapPhase(phase="medium", title="Médio prazo", items=medium[:12]),
    ]

    baseline_section: BaselineDiffSection | None = None
    if baseline is not None:
        adiff = diff_analysis_results(baseline, result)
        sem_ins, sem_imp, sem_wor, sem_risk = semantic_diff_from_analyses_only(baseline, result)
        baseline_section = BaselineDiffSection(
            has_baseline=True,
            methodology_changed=adiff.methodology_changed,
            max_risk_delta=adiff.max_risk_delta,
            threats_added=[x.threat_id for x in adiff.heuristic_threats.added],
            threats_removed=[x.threat_id for x in adiff.heuristic_threats.removed],
            threats_modified=[x.threat_id for x in adiff.heuristic_threats.modified],
            recurring_signatures=adiff.signature_remap_hints,
            trust_boundary_delta_summary=(
                f"Achados de fronteira: {adiff.trust_boundary_findings.count_before} → "
                f"{adiff.trust_boundary_findings.count_after}"
                if adiff.trust_boundary_findings
                else ""
            ),
            structural_delta_summary=(
                f"Estruturais: {adiff.structural_findings.count_before} → {adiff.structural_findings.count_after}"
                if adiff.structural_findings
                else ""
            ),
            narrative=(
                f"Delta de score máximo: {adiff.max_risk_delta}; "
                f"ameaças adicionadas {len(adiff.heuristic_threats.added)}, "
                f"removidas {len(adiff.heuristic_threats.removed)}."
            ),
            semantic_improved=sem_imp[:12],
            semantic_worsened=sem_wor[:12],
            semantic_risk_impact=sem_risk[:8],
            semantic_insights_from_analysis=sem_ins[:14],
        )

    dedupe: list[DedupeGroup] = build_dedupe_groups(active, meth, doc)

    explain_snippets = [
        ExplainabilitySnippet(
            record_id=e.id,
            category=str(e.category),
            message=e.message[:800],
            confidence=e.confidence,
        )
        for e in result.explanations[:40]
    ]

    tech_appendix: TechnicalAppendix | None = None
    if level == ReportLevel.DEEP:
        lines = []
        for t in active:
            lines.append(f"### {t.id} — {t.title}\n{t.description}\n")
        for t in doc.threats:
            lines.append(f"### [canónica] {t.id} — {t.title}\n{t.description or ''}\n")
        tech_appendix = TechnicalAppendix(
            full_threat_listing="\n".join(lines)[:120000],
            methodology_outputs_note=(
                "Outputs específicos do engine por metodologia estão em `analysis_json` e em "
                "`methodology_insights` / `ai_system_context` quando aplicável."
            ),
            import_evidence_note=(
                "Texto de importação presente em `import_signals_corpus` no documento canónico."
                if doc.import_signals_corpus
                else None
            ),
        )

    disclaimer = InferenceDisclaimer(
        summary=(
            "Ownership, exploitability e impacto de negócio são inferências heurísticas para acelerar decisão. "
            "Não representam auditoria nem garantia de exploração real."
        ),
        bullets=[
            "Priorização composta (P1/P2/P3) combina score, exposição e esforço estimado.",
            "Recomendações estratégicas devem ser validadas contra políticas internas.",
        ],
    )

    cover = CoverPage(
        title=doc.metadata.title,
        model_id_hint=doc.metadata.document_version or doc.metadata.title[:48],
        document_version=doc.metadata.document_version,
        schema_version=doc.model_info.schema_version,
        primary_methodology=meth.value,
        complementary_methodologies=[],
        system_type=doc.model_info.system_type.value,
        industry_sector=doc.model_info.industry_sector.value,
        analysis_date_iso=date.today().isoformat(),
        app_suite_version=app_v,
        overall_risk_label=_risk_label(max_score),
        overall_status=status_key,
        overall_status_display=status_display,
    )

    exec_summary = ExecutiveSummaryBlock(
        threat_count=total_threats,
        severity_distribution=dict(sev_counter),
        methodology_distribution=methodology_dist,
        top_trust_boundaries=top_boundaries,
        top_attack_surfaces=[str(x) for x in top_surfaces if x],
        top5_risk_titles=top5_titles,
        business_impact_summary=(
            "Principais vectores: confidencialidade, integridade e disponibilidade — "
            "ver secção de impacto por ameaça."
        ),
        urgency_level=urgency,
        executive_conclusion=exec_conclusion,
        readiness_questions=readiness,
    )

    guided_audit: GuidedModelingAuditBlock | None = None
    trace_lines = [
        f"{e.source_tag} → {e.effect} ({e.weight}): {e.explanation[:220]}"
        for e in result.wizard_signal_trace[:14]
    ]
    gap_msgs: list[str] = []
    if result.model_quality_precheck and result.model_quality_precheck.checks:
        gap_msgs = [c.message for c in result.model_quality_precheck.checks if not c.passed][:8]
    ap_summaries = [
        f"{h.name} (`{h.id}`) · conf. {getattr(h, 'confidence_hint', None) or 'medium'}"
        for h in result.anti_pattern_hits[:10]
    ]
    mq_line = None
    if result.model_quality_precheck:
        pqx = result.model_quality_precheck
        mq_line = (
            f"Pré-check {pqx.score_0_100}/100 ({pqx.band}); "
            f"confiança recomendações: {pqx.recommendation_confidence}."
        )
    mc_line = None
    if result.methodology_completeness:
        mc = result.methodology_completeness
        mc_line = f"Completude metodológica: {mc.state.value}."
        if mc.note:
            mc_line += f" {mc.note[:160]}"

    if (
        result.wizard_context_notes
        or trace_lines
        or gap_msgs
        or ap_summaries
        or mq_line
        or mc_line
    ):
        guided_audit = GuidedModelingAuditBlock(
            model_quality_summary_line=mq_line,
            methodology_completeness_line=mc_line,
            wizard_context_notes=list(result.wizard_context_notes[:8]),
            wizard_signal_trace_lines=trace_lines,
            top_model_gap_messages=gap_msgs,
            anti_pattern_summaries=ap_summaries,
        )

    return PremiumReportPayload(
        level=level,
        disclaimer=disclaimer,
        cover=cover,
        executive_summary=exec_summary,
        architecture=arch,
        distributions=distributions,
        top_risks=top_risks,
        root_cause_groups=rc_groups[:20],
        exploitability_profiles=exploit_profiles,
        business_impacts=business_rows,
        quick_wins=quick_wins,
        ownership=ownership_rows[:15],
        strategic_recommendations=strategic[:12],
        roadmap=roadmap,
        baseline_diff=baseline_section,
        deduplication=dedupe,
        explainability=explain_snippets,
        technical_appendix=tech_appendix,
        methodology_voice=methodology_voice_lines(meth),
        guided_modeling_audit=guided_audit,
    )


def diff_analysis_for_report(
    baseline: AnalysisResult,
    revised: AnalysisResult,
):
    """Expõe o diff do motor para consumo externo (testes, API)."""
    return diff_analysis_results(baseline, revised)
