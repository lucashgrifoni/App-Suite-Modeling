"""
Constrói `PremiumReportPayload` a partir do documento canónico, análise, backlog e diff opcional.

Toda a lógica pesada de negócio permanece no motor e no backlog; aqui apenas agregamos vistas.
"""

from __future__ import annotations

import importlib.metadata
from collections import Counter, defaultdict
from datetime import date
from typing import Any, Literal

from otm_core_schema import ComponentKind
from otm_core_schema.document import ThreatModelDocument
from otm_core_schema.trust_membership import resolve_component_boundaries
from otm_diagram_engine import export_flowchart_mermaid
from otm_exporters.markdown_text import md_block, md_inline
from otm_threat_engine import build_remediation_backlog
from otm_threat_engine.analysis_diff import diff_analysis_results
from otm_threat_engine.methodologies import recommend_methodology
from otm_threat_engine.remediation.classify import ComponentIndex
from otm_threat_engine.result import AnalysisResult, HeuristicThreat
from otm_threat_engine.semantic_comparison import semantic_diff_from_analyses_only
from otm_threat_engine.severity import severity_at_least, severity_for_score

from .dedupe import build_dedupe_groups
from .enums import ReportLevel
from .i18n_locale import PremiumReportLocale, normalize_premium_locale
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
from .report_i18n import PremiumBuilderCopy, premium_builder_copy, root_cause_display_name
from .risk_context import (
    ai_business_labels_if_applicable,
    build_business_impact_row,
    infer_exploitability,
)


def _app_version() -> str:
    try:
        return importlib.metadata.version("open-threat-model")
    except importlib.metadata.PackageNotFoundError:  # pragma: no cover - defensive: package always installed
        return "unknown"


def _band_for_score(raw: float) -> str:
    """Delegates to the engine's canonical band so the report and `otm analyze` agree."""
    return severity_for_score(raw)


def _severity_band(t: HeuristicThreat) -> str:
    raw = t.risk.score if t.risk.score is not None else float(t.risk.likelihood * t.risk.impact)
    return _band_for_score(raw)


def _overall_max_score(heuristic_max: float | None, doc: ThreatModelDocument) -> float | None:
    """O maior risco que o relatório mostra, venha de onde vier."""
    scores = [heuristic_max] if heuristic_max is not None else []
    scores += [
        float(t.risk.likelihood * t.risk.impact)
        for t in doc.threats
        if t.risk is not None and t.risk.likelihood is not None and t.risk.impact is not None
    ]
    return max(scores) if scores else None


def _overall_status(
    max_score: float | None, b: PremiumBuilderCopy
) -> tuple[
    Literal["requires_immediate_attention", "action_recommended", "acceptable_with_follow_up"],
    str,
]:
    if max_score is None:
        return "acceptable_with_follow_up", b.status_acceptable_no_aggregate
    if max_score >= 20:
        return "requires_immediate_attention", b.status_requires_immediate
    if max_score >= 12:
        return "action_recommended", b.status_action_recommended
    return "acceptable_with_follow_up", b.status_acceptable_plain


def _risk_label(max_score: float | None, b: PremiumBuilderCopy) -> str:
    """Narrative adjective for the cover and executive conclusion.

    Keeps its own vocabulary (*elevated* / *high* / *medium* / *low to moderate*) but must use
    the SAME cut points as `severity_for_score`. A second set of thresholds here is precisely
    what made one document call the same score "medium" on the cover and "High" in its own
    severity table.
    """
    if max_score is None:
        return b.risk_not_calculated
    band = severity_for_score(max_score)
    if band == "critical":
        return b.risk_elevated
    if band == "high":
        return b.risk_high
    if band == "medium":
        return b.risk_medium
    return b.risk_low_moderate


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


def _trust_boundary_by_component(doc: ThreatModelDocument) -> dict[str, str]:
    """As duas formas de declarar a pertença, juntas — que é o que o motor já fazia.

    Ler só `Component.in_trust_boundary` imprimia "Principais trust boundaries: _Nenhuma listada._"
    para um documento cujas fronteiras estão declaradas do lado da fronteira, no mesmo relatório
    que reportava `trust_perimeter_crossing`: uma contradição dentro da mesma página.
    """
    return resolve_component_boundaries(doc)


def _build_distribution_counters(
    active: list[HeuristicThreat], doc: ThreatModelDocument, tb_by_component: dict[str, str]
) -> tuple[Counter[str], Counter[str], Counter[str], Counter[str], dict[str, dict[str, int]]]:
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
            # `likelihood x impact` e nao `score`. A banda vem de `severity_for_score`, cujo
            # docstring fixa o dominio: "o score L×I (1–5)", com limiares 20/12/6 nessa escala.
            # No esquema `likelihood` e `impact` sao obrigatorios e validados em 1–5, enquanto
            # `score` e opcional e a sua descricao admite outra escala — "Ex.: L×I ou
            # normalizado". Um valor CVSS (0–10) escrito ali e legitimo e rebaixava a banda: uma
            # ameaca L5×I5 com score 9.8 saia `medium` no quadro ao lado de uma capa a dizer
            # "Requer atenção imediata", que ja lia `likelihood x impact` em `_overall_max_score`.
            # Para as heuristicas nao muda nada: `build_risk_assessment` grava `score = L×I`.
            raw = float(threat.risk.likelihood * threat.risk.impact)
            band = _band_for_score(raw)
            sev_counter[band] += 1
            # O mapa também: este ciclo alimentava STRIDE, severidade e componente e saltava o
            # `heatmap`, por isso o quadro STRIDE x severidade contava menos ameaças do que a
            # tabela impressa ao lado dele, na mesma página. E o efeito era pior do que uma
            # contagem a menos: a heurística equivalente é suprimida como duplicada quando o
            # modelador declara a sua própria, portanto declarar a ameaça **apagava** a linha do
            # mapa em vez de a mover de banda.
            heatmap[threat.stride.value][band] += 1
        if threat.target_component_id:
            comp_counter[threat.target_component_id] += 1
    return sev_counter, stride_counter, comp_counter, tb_counter, heatmap


def _urgency_level(score: float) -> Literal["high", "medium", "low"]:
    """Three-level urgency, collapsed from the canonical band (critical and high both urgent)."""
    band = severity_for_score(score)
    if severity_at_least(band, "high"):
        return "high"
    if band == "medium":
        return "medium"
    return "low"


def _build_architecture(
    doc: ThreatModelDocument,
    b: PremiumBuilderCopy,
    meth: Any,
    recommendation: Any,
    *,
    include_mermaid: bool,
    level: ReportLevel,
) -> ArchitectureSummary:
    arch_narrative_parts: list[str] = []
    if doc.business_context and doc.business_context.description:
        arch_narrative_parts.append(doc.business_context.description)
    arch_narrative_parts.append(
        b.arch_counts.format(
            n_comp=len(doc.components),
            n_flows=len(doc.data_flows),
            n_tb=len(doc.trust_boundaries),
        )
    )
    return ArchitectureSummary(
        narrative=" ".join(arch_narrative_parts),
        main_components=[c.name for c in doc.components[:12]],
        main_flows=[f.name or f.id for f in doc.data_flows[:12]],
        trust_boundaries=[b.name for b in doc.trust_boundaries],
        external_dependencies=[c.name for c in doc.components if c.kind == ComponentKind.EXTERNAL_ENTITY][:10],
        sensitive_assets=[
            a.name for a in doc.assets if (a.sensitivity or "").lower() in ("confidential", "restricted", "high")
        ][:10],
        methodology_used=meth.value,
        methodology_recommended=recommendation.methodology.value,
        recommendation_reason=recommendation.reason,
        mermaid_flowchart=export_flowchart_mermaid(doc) if include_mermaid and level == ReportLevel.DEEP else None,
    )


def _build_distributions(
    *,
    total_threats: int,
    sev_counter: Counter[str],
    stride_counter: Counter[str],
    comp_counter: Counter[str],
    tb_counter: Counter[str],
    heatmap: dict[str, dict[str, int]],
    methodology_dist: dict[str, int],
    comp_names: dict[str, str],
    doc: ThreatModelDocument,
    backlog: Any,
    active: list[HeuristicThreat],
    meth: Any,
    tb_by_component: dict[str, str],
    index: ComponentIndex,
) -> DistributionBlock:
    comp_scores: dict[str, float] = defaultdict(float)
    for t in active:
        if t.target_component_id:
            comp_scores[t.target_component_id] += composite_priority_score(t, doc, meth, index=index)
    tb_scores: dict[str, float] = defaultdict(float)
    for cid, sc in comp_scores.items():
        bid = tb_by_component.get(cid)
        if bid:
            tb_scores[bid] += sc
    top_comp_ranked = sorted(comp_scores.items(), key=lambda x: -x[1])[:10]
    top_tb_ranked = sorted(tb_scores.items(), key=lambda x: -x[1])[:10]

    return DistributionBlock(
        total_threats=total_threats,
        by_severity_band=dict(sev_counter),
        by_stride=dict(stride_counter),
        by_methodology_tag=methodology_dist,
        by_component={comp_names.get(k, k): v for k, v in comp_counter.most_common(15)},
        by_trust_boundary={_boundary_name(doc, k) or k: v for k, v in tb_counter.most_common(15)},
        by_risk_type=dict(stride_counter),
        by_control_domain=dict(Counter(b.control_category for b in backlog.items)),
        heatmap_stride_severity={sk: dict(sv) for sk, sv in heatmap.items()},
        top_components_ranked=[(comp_names.get(c, c), s) for c, s in top_comp_ranked],
        top_boundaries_ranked=[(_boundary_name(doc, b) or b, s) for b, s in top_tb_ranked],
    )


def _build_top_risks(
    sorted_threats: list[HeuristicThreat],
    doc: ThreatModelDocument,
    meth: Any,
    backlog: Any,
    b: PremiumBuilderCopy,
    index: ComponentIndex,
) -> list[TopRiskItem]:
    top_risks: list[TopRiskItem] = []
    for i, t in enumerate(sorted_threats[:10]):
        tier = assign_priority_tier(i, min(10, len(sorted_threats)))
        ex = infer_exploitability(t, doc, index=index)
        bi_labels = build_business_impact_row(t).labels + ai_business_labels_if_applicable(t)
        backlog_match = next(
            (b for b in backlog.items if any(r.id == t.id for r in b.related_findings if r.kind == "heuristic_threat")),
            None,
        )
        action = backlog_match.next_step if backlog_match else b.default_threat_action.format(threat_id=t.id)
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
                composite_score=composite_priority_score(t, doc, meth, index=index),
                recommended_action=action,
                suggested_horizon=horizon_for_tier(tier),
            )
        )
    return top_risks


def _build_root_cause_groups(backlog: Any, loc: PremiumReportLocale) -> list[RootCauseGroup]:
    rc_groups: list[RootCauseGroup] = []
    # `item_ids` visto como conjunto. Testar pertença contra uma **lista**, uma vez por item e
    # por grupo, é O(grupos x itens x ids): 0,44 s num único relatório de 1500 entidades, e a
    # crescer ao quadrado. A iteração continua a ser sobre `backlog.items`, para o grupo manter
    # exactamente a mesma ordem de antes.
    for root_key, item_ids in backlog.by_root_cause.items():
        wanted = set(item_ids)
        items = [i for i in backlog.items if i.id in wanted]
        if not items:
            continue  # pragma: no cover - defensive guard
        comps: set[str] = set()
        for it in items:
            comps.update(it.related_components)
        # `list(set(...))` here made the premium report non-reproducible: two runs of the same
        # command over the same model emitted `data_protection, hardening_and_integrity` and its
        # reverse, because set iteration order follows the per-process hash seed. Worse, once a
        # group holds more than six distinct control types the `[:6]` slice would have dropped a
        # *different* control each run. `dict.fromkeys` deduplicates in backlog order, which is
        # the order the six kept controls should be chosen in anyway.
        controls = list(dict.fromkeys(it.suggested_control_type for it in items))[:6]
        rc_groups.append(
            RootCauseGroup(
                key=root_key,
                display_name=root_cause_display_name(root_key, loc),
                threat_count=len(items),
                component_ids=sorted(comps)[:20],
                suggested_controls=controls,
                single_fix_recommendation=items[0].rationale[:500] if items else "",
            )
        )
    rc_groups.sort(key=lambda x: -x.threat_count)
    return rc_groups


def _build_quick_wins(backlog: Any) -> list[QuickWinItem]:
    quick_wins: list[QuickWinItem] = []
    for qid in backlog.quick_win_ids[:15]:
        item = next((i for i in backlog.items if i.id == qid), None)
        if not item:
            continue  # pragma: no cover - defensive guard
        quick_wins.append(
            QuickWinItem(
                backlog_item_id=qid,
                title=item.title,
                rationale=item.quick_win_explanation or item.rationale,
            )
        )
    return quick_wins


def _build_ownership_rows(backlog: Any, b: PremiumBuilderCopy) -> list[OwnershipRow]:
    ownership_rows: list[OwnershipRow] = []
    owner_buckets: dict[str, list[str]] = defaultdict(list)
    for it in backlog.items:
        role = it.recommended_owner or "a_definir"
        owner_buckets[role].append(it.id)
    for role, ids in sorted(owner_buckets.items(), key=lambda x: -len(x[1])):
        display_role = b.owner_pending_display if role == "a_definir" else role
        ownership_rows.append(
            OwnershipRow(
                scope=b.ownership_scope.format(role=display_role),
                suggested_owner_role=None if role == "a_definir" else role,
                explanation=b.ownership_explanation,
                backlog_item_ids=ids[:30],
                item_count=len(ids),
            )
        )
    return ownership_rows


def _build_strategic(result: AnalysisResult, b: PremiumBuilderCopy) -> list[StrategicRecommendation]:
    strategic: list[StrategicRecommendation] = [
        StrategicRecommendation(
            title=b.strategic_baseline_title,
            detail=b.strategic_baseline_detail,
        ),
        StrategicRecommendation(
            title=b.strategic_integrations_title,
            detail=b.strategic_integrations_detail,
        ),
    ]
    for hint in result.pack_control_hints[:5]:
        strategic.append(
            StrategicRecommendation(title=b.strategic_pack_title, detail=hint[:400]),
        )
    return strategic


def _build_roadmap(backlog: Any, b: PremiumBuilderCopy) -> list[RoadmapPhase]:
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
    return [
        RoadmapPhase(phase="immediate", title=b.roadmap_immediate, items=immediate[:12]),
        RoadmapPhase(phase="short", title=b.roadmap_short, items=short_term[:12]),
        RoadmapPhase(phase="medium", title=b.roadmap_medium, items=medium[:12]),
    ]


def _build_baseline_section(
    baseline: AnalysisResult | None, result: AnalysisResult, b: PremiumBuilderCopy
) -> BaselineDiffSection | None:
    if baseline is None:
        return None
    adiff = diff_analysis_results(baseline, result)
    sem_ins, sem_imp, sem_wor, sem_risk = semantic_diff_from_analyses_only(baseline, result)
    return BaselineDiffSection(
        has_baseline=True,
        methodology_changed=adiff.methodology_changed,
        max_risk_delta=adiff.max_risk_delta,
        threats_added=[x.threat_id for x in adiff.heuristic_threats.added],
        threats_removed=[x.threat_id for x in adiff.heuristic_threats.removed],
        threats_modified=[x.threat_id for x in adiff.heuristic_threats.modified],
        recurring_signatures=adiff.signature_remap_hints,
        trust_boundary_delta_summary=(
            b.tb_delta.format(
                before=adiff.trust_boundary_findings.count_before,
                after=adiff.trust_boundary_findings.count_after,
            )
            if adiff.trust_boundary_findings
            else ""
        ),
        structural_delta_summary=(
            b.struct_delta.format(
                before=adiff.structural_findings.count_before,
                after=adiff.structural_findings.count_after,
            )
            if adiff.structural_findings
            else ""
        ),
        narrative=b.baseline_narrative.format(
            delta=adiff.max_risk_delta,
            added=len(adiff.heuristic_threats.added),
            removed=len(adiff.heuristic_threats.removed),
        ),
        semantic_improved=sem_imp[:12],
        semantic_worsened=sem_wor[:12],
        semantic_risk_impact=sem_risk[:8],
        semantic_insights_from_analysis=sem_ins[:14],
    )


def _build_explain_snippets(result: AnalysisResult) -> list[ExplainabilitySnippet]:
    return [
        ExplainabilitySnippet(
            record_id=e.id,
            category=str(e.category),
            message=e.message[:800],
            confidence=e.confidence,
        )
        for e in result.explanations[:40]
    ]


#: Orçamento de caracteres da listagem do apêndice no payload. Existe para o relatório de um
#: modelo com milhares de ameaças não crescer sem limite; não é um contrato de conteúdo.
_APPENDIX_LISTING_BUDGET = 120_000


def _appendix_entries_within_budget(entries: list[str], budget: int) -> list[str]:
    """As primeiras entradas **inteiras** que cabem no orçamento.

    Cortar por caracteres partia a última entrada a meio da palavra e entregava-a assim ao leitor,
    indistinguível de um ficheiro corrompido. O corte passa a ser por entrada. Se nem a primeira
    couber, é mantida na mesma: um apêndice vazio esconderia tudo, e o tamanho da entrada já está
    limitado a montante pelos limites de tamanho do documento.
    """
    kept: list[str] = []
    used = 0
    for entry in entries:
        cost = len(entry) + (1 if kept else 0)  # o "\n" que junta esta entrada à anterior
        if kept and used + cost > budget:
            break
        kept.append(entry)
        used += cost
    return kept


def _build_tech_appendix(
    doc: ThreatModelDocument, active: list[HeuristicThreat], b: PremiumBuilderCopy, level: ReportLevel
) -> TechnicalAppendix | None:
    if level != ReportLevel.DEEP:
        return None
    # `md_inline`/`md_block` no texto do modelo: cada entrada é escrita como um `### …` seguido da
    # descrição no princípio da linha seguinte, portanto um título ou uma descrição com quebras de
    # linha (ou que já comece por `###`) forjava entradas de apêndice que ninguém escreveu — e o
    # renderizador HTML volta a ler esta listagem como estrutura para montar a tabela do PDF.
    entries = [f"### {md_inline(t.id)} — {md_inline(t.title)}\n{md_block(t.description)}\n" for t in active]
    entries += [
        f"### {b.threat_canonical_prefix} {md_inline(c_threat.id)} — {md_inline(c_threat.title)}\n"
        f"{md_block(c_threat.description or '')}\n"
        for c_threat in doc.threats
    ]
    listed = _appendix_entries_within_budget(entries, _APPENDIX_LISTING_BUDGET)
    return TechnicalAppendix(
        full_threat_listing="\n".join(listed),
        total_threat_count=len(entries),
        methodology_outputs_note=b.tech_methodology_outputs,
        import_evidence_note=(b.tech_import_evidence if doc.import_signals_corpus else None),
    )


def _build_cover(
    doc: ThreatModelDocument,
    meth: Any,
    app_v: str,
    max_score: float | None,
    status_key: Literal["requires_immediate_attention", "action_recommended", "acceptable_with_follow_up"],
    status_display: str,
    b: PremiumBuilderCopy,
) -> CoverPage:
    return CoverPage(
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
        overall_risk_label=_risk_label(max_score, b),
        overall_status=status_key,
        overall_status_display=status_display,
    )


def _build_exec_summary(
    *,
    total_threats: int,
    sev_counter: Counter[str],
    methodology_dist: dict[str, int],
    top_boundaries: list[str],
    top_surfaces: list[str],
    top5_titles: list[str],
    urgency: Literal["high", "medium", "low"],
    exec_conclusion: str,
    readiness: list[str],
    b: PremiumBuilderCopy,
) -> ExecutiveSummaryBlock:
    return ExecutiveSummaryBlock(
        threat_count=total_threats,
        severity_distribution=dict(sev_counter),
        methodology_distribution=methodology_dist,
        top_trust_boundaries=top_boundaries,
        top_attack_surfaces=[str(x) for x in top_surfaces if x],
        top5_risk_titles=top5_titles,
        business_impact_summary=b.business_impact_summary,
        urgency_level=urgency,
        executive_conclusion=exec_conclusion,
        readiness_questions=readiness,
    )


def _build_guided_audit(result: AnalysisResult, b: PremiumBuilderCopy) -> GuidedModelingAuditBlock | None:
    trace_lines = [
        b.wizard_trace.format(
            source_tag=e.source_tag,
            effect=e.effect,
            weight=e.weight,
            explanation=e.explanation[:220],
        )
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
        mq_line = b.mq_line.format(
            score=pqx.score_0_100,
            band=pqx.band,
            conf=pqx.recommendation_confidence,
        )
    mc_line = None
    if result.methodology_completeness:
        mc = result.methodology_completeness
        mc_line = f"{b.mc_line_prefix} {mc.state.value}."
        if mc.note:
            mc_line += f" {mc.note[:160]}"

    if result.wizard_context_notes or trace_lines or gap_msgs or ap_summaries or mq_line or mc_line:
        return GuidedModelingAuditBlock(
            model_quality_summary_line=mq_line,
            methodology_completeness_line=mc_line,
            wizard_context_notes=list(result.wizard_context_notes[:8]),
            wizard_signal_trace_lines=trace_lines,
            top_model_gap_messages=gap_msgs,
            anti_pattern_summaries=ap_summaries,
        )
    return None


def build_premium_report_payload(
    doc: ThreatModelDocument,
    result: AnalysisResult,
    *,
    level: ReportLevel,
    baseline: AnalysisResult | None = None,
    app_version: str | None = None,
    include_mermaid: bool = True,
    locale: str | None = None,
) -> PremiumReportPayload:
    """
    Constrói o payload premium. `baseline` opcional alimenta secção de diff/trend.

    ``locale`` opcional: ``pt-BR`` (omissão) ou ``en`` após normalização na API.
    """
    loc: PremiumReportLocale = normalize_premium_locale(locale)
    b = premium_builder_copy(loc)
    meth = result.methodology
    active: list[HeuristicThreat] = [h for h in result.heuristic_threats if not h.skipped_as_duplicate]
    backlog = build_remediation_backlog(result, doc)
    recommendation = recommend_methodology(doc)
    app_v = app_version or _app_version()

    max_score = result.summary.max_risk_score
    # O **estado geral** olha para as duas origens; o rótulo de risco continua a ser o heurístico.
    # `summary.max_risk_score` conta só heurísticas, e a capa classificava por ele — por isso um
    # documento cuja única ameaça crítica é declarada pelo modelador (L5xI5 = 25) saía como
    # "Aceitável com acompanhamento", exactamente igual ao mesmo documento sem ela. O relatório
    # já contava essa ameaça no total, que descreve como "canónicas + heurísticas activas", e no
    # quadro de severidade: era o veredito da capa que discordava do resto da própria página.
    # O rótulo diz `Risk (heuristic)` no HTML e continua a medir isso, senão o rótulo é que
    # passava a mentir. Ver `tests/test_p3_premium_cover_sees_declared_threats.py`.
    status_key, status_display = _overall_status(_overall_max_score(max_score, doc), b)

    comp_names = {c.id: c.name for c in doc.components}
    # Um índice para todo o pipeline: sem ele cada classificação por ameaça revarre
    # `doc.components` (ver `ComponentIndex`).
    index = ComponentIndex.of(doc)
    tb_by_component = _trust_boundary_by_component(doc)

    sev_counter, stride_counter, comp_counter, tb_counter, heatmap = _build_distribution_counters(
        active, doc, tb_by_component
    )

    methodology_dist = {meth.value: len(active) + len(doc.threats)}
    total_threats = len(active) + len(doc.threats)

    top_boundaries = [_boundary_name(doc, bid) or bid for bid, _n in tb_counter.most_common(5)]
    top_surfaces = [comp_names.get(cid, cid) for cid, _n in comp_counter.most_common(5)]

    sorted_threats = sorted(
        active,
        key=lambda x: composite_priority_score(x, doc, meth, index=index),
        reverse=True,
    )
    top5_titles = [t.title for t in sorted_threats[:5]]

    # As três leituras da mesma página têm de concordar. `_overall_status` já usa o máximo das duas
    # origens; estas duas ficaram na pontuação só-heurística, e o relatório executivo saía a dizer
    # "Requer atenção imediata", "Urgência: medium" e "critical | 1" no mesmo bloco.
    overall_max = _overall_max_score(max_score, doc)
    urgency = _urgency_level(overall_max or 0)

    readiness = [
        b.readiness_high if severity_at_least(severity_for_score(overall_max or 0), "high") else b.readiness_moderate,
        b.readiness_release,
        b.readiness_compensating,
    ]

    exec_conclusion = b.exec_conclusion.format(
        total_threats=total_threats,
        risk_label=_risk_label(max_score, b),
    )

    arch = _build_architecture(doc, b, meth, recommendation, include_mermaid=include_mermaid, level=level)

    distributions = _build_distributions(
        total_threats=total_threats,
        sev_counter=sev_counter,
        stride_counter=stride_counter,
        comp_counter=comp_counter,
        tb_counter=tb_counter,
        heatmap=heatmap,
        methodology_dist=methodology_dist,
        comp_names=comp_names,
        doc=doc,
        backlog=backlog,
        active=active,
        meth=meth,
        tb_by_component=tb_by_component,
        index=index,
    )

    top_risks = _build_top_risks(sorted_threats, doc, meth, backlog, b, index)
    rc_groups = _build_root_cause_groups(backlog, loc)

    exploit_profiles = [infer_exploitability(t, doc, index=index) for t in sorted_threats[:15]]
    business_rows = [build_business_impact_row(t) for t in sorted_threats[:15]]

    quick_wins = _build_quick_wins(backlog)
    ownership_rows = _build_ownership_rows(backlog, b)
    strategic = _build_strategic(result, b)
    roadmap = _build_roadmap(backlog, b)
    baseline_section = _build_baseline_section(baseline, result, b)
    dedupe: list[DedupeGroup] = build_dedupe_groups(active, meth, doc, index=index)
    explain_snippets = _build_explain_snippets(result)
    tech_appendix = _build_tech_appendix(doc, active, b, level)

    disclaimer = InferenceDisclaimer(
        summary=b.disclaimer_summary,
        bullets=[b.disclaimer_b1, b.disclaimer_b2],
    )
    cover = _build_cover(doc, meth, app_v, max_score, status_key, status_display, b)
    exec_summary = _build_exec_summary(
        total_threats=total_threats,
        sev_counter=sev_counter,
        methodology_dist=methodology_dist,
        top_boundaries=top_boundaries,
        top_surfaces=top_surfaces,
        top5_titles=top5_titles,
        urgency=urgency,
        exec_conclusion=exec_conclusion,
        readiness=readiness,
        b=b,
    )
    guided_audit = _build_guided_audit(result, b)

    return PremiumReportPayload(
        locale=loc,
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
        methodology_voice=methodology_voice_lines(meth, loc),
        guided_modeling_audit=guided_audit,
    )


def diff_analysis_for_report(
    baseline: AnalysisResult,
    revised: AnalysisResult,
):
    """Expõe o diff do motor para consumo externo (testes, API)."""
    return diff_analysis_results(baseline, revised)
