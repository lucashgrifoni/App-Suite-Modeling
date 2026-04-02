"""
Insights semânticos para comparação de modelos (além do diff JSON).

Alimenta `ThreatModelComparisonResult.meta` com bullets acionáveis para UI/relatórios.
"""

from __future__ import annotations

from typing import Any

from otm_core_schema import ThreatModelDocument
from otm_core_schema.enums import ComponentKind

from otm_threat_engine.comparison_models import DiffAggregate
from otm_threat_engine.result import AnalysisResult


def enrich_comparison_meta(
    baseline: ThreatModelDocument,
    revised: ThreatModelDocument,
    *,
    baseline_analysis: AnalysisResult | None,
    revised_analysis: AnalysisResult | None,
    aggregate: DiffAggregate,
) -> dict[str, Any]:
    """Devolve chaves a fundir em `meta` (ex.: semantic_insights)."""
    insights: list[str] = []
    improved: list[str] = []
    worsened: list[str] = []
    risk_impact: list[str] = []

    comp_add = aggregate.components["added"]
    r_by_id = {c.id: c for c in revised.components}
    b_by_id = {c.id: c for c in baseline.components}
    for cid in comp_add:
        c = r_by_id.get(cid)
        if not c:
            continue
        if c.kind == ComponentKind.GATEWAY:
            insights.append(
                "Novo gateway: política de perímetro e encaminhamento deverão ser revistos; "
                "impacto típico em spoofing e negação de serviço no perímetro."
            )
            risk_impact.append("Superfície de controlo de entrada alterada (gateway).")
        if c.kind == ComponentKind.EXTERNAL_ENTITY:
            insights.append(
                "Nova entidade externa: confiança e integridade de integrações aumentam relevância "
                "para spoofing e exposição de dados."
            )
        if c.kind == ComponentKind.DATASTORE:
            insights.append(
                f"Novo datastore `{cid}`: rever backup, segregação e classificação de dados em repouso."
            )
            worsened.append("Persistência adicional — aumenta superfície de dados sensíveis.")
    comp_rem = aggregate.components["removed"]
    for cid in comp_rem:
        c = b_by_id.get(cid)
        if c and c.kind == ComponentKind.DATASTORE:
            improved.append(f"Datastore `{cid}` removido — superfície de dados pode ter diminuído.")

    tb_add = aggregate.trust_boundaries["added"]
    for bid in tb_add:
        insights.append(
            f"Nova trust boundary `{bid}`: mapear fluxos que a cruzam e controlos de segmentação."
        )
        risk_impact.append("Segmentação de rede/perímetro mais explícita; revisar crossing flows.")
    tb_rem = aggregate.trust_boundaries["removed"]
    for bid in tb_rem:
        insights.append(
            f"Trust boundary `{bid}` removida: rede de confiança e superfície de ataque podem ter mudado."
        )
        worsened.append(f"Remoção de boundary `{bid}` — possível perda de visibilidade de perímetro.")

    for aid in aggregate.assets["added"]:
        insights.append(f"Novo ativo `{aid}`: rever classificação, impacto e priorização.")
    for aid in aggregate.assets["removed"]:
        insights.append(f"Ativo `{aid}` removido — verificar se dados sensíveis deixaram de estar modelados.")
        improved.append(f"Ativo `{aid}` removido — escopo de dados pode ter diminuído.")

    flow_changed = aggregate.data_flows["changed"]
    if flow_changed:
        risk_impact.append(
            f"{len(flow_changed)} fluxo(s) com alterações de metadados — rever sensibilidade/autenticação."
        )

    if baseline_analysis is not None and revised_analysis is not None:
        bq = baseline_analysis.model_quality_precheck
        rq = revised_analysis.model_quality_precheck
        if bq is not None and rq is not None and bq.score_0_100 != rq.score_0_100:
            delta = rq.score_0_100 - bq.score_0_100
            insights.append(
                f"Pré-check de qualidade: score {bq.score_0_100} → {rq.score_0_100} "
                f"(banda {bq.band} → {rq.band})."
            )
            if delta > 0:
                improved.append(f"Model quality +{delta} pts — modelo mais completo ou explícito.")
            elif delta < 0:
                worsened.append(f"Model quality {delta} pts — regressão de completude ou contexto.")

        bc = baseline_analysis.methodology_completeness
        rc = revised_analysis.methodology_completeness
        if (
            bc is not None
            and rc is not None
            and bc.state.value != rc.state.value
        ):
            insights.append(
                f"Completude metodológica: {bc.state.value} → {rc.state.value}; "
                "rever interpretação dos achados."
            )
            if rc.state.value == "degraded":
                worsened.append("Metodologia degrada — achados podem estar mais fracos ou genéricos.")
            else:
                improved.append("Estado metodológico alterado — alinhar leitura ao novo contexto.")

        bs = baseline_analysis.summary.heuristic_threats_skipped_duplicate
        rs = revised_analysis.summary.heuristic_threats_skipped_duplicate
        if bs != rs:
            insights.append(
                f"Ruído heurístico (duplicados suprimidos): {bs} → {rs} — comparar relevância dos top risks."
            )

        ap_b = {h.id for h in baseline_analysis.anti_pattern_hits}
        ap_r = {h.id for h in revised_analysis.anti_pattern_hits}
        added_ap = ap_r - ap_b
        removed_ap = ap_b - ap_r
        if added_ap:
            worsened.append(
                f"Novos anti-padrões de modelagem: {', '.join(sorted(added_ap)[:5])}"
                + ("…" if len(added_ap) > 5 else "")
            )
        if removed_ap:
            improved.append(
                f"Anti-padrões deixaram de aplicar: {', '.join(sorted(removed_ap)[:5])}"
                + ("…" if len(removed_ap) > 5 else "")
            )

        def _top_ids(ar: AnalysisResult) -> list[str]:
            active = [h for h in ar.heuristic_threats if not h.skipped_as_duplicate]
            top = sorted(active, key=lambda h: -(h.risk.score or 0))[:5]
            return [h.id for h in top]

        t_b = _top_ids(baseline_analysis)
        t_r = _top_ids(revised_analysis)
        if t_b != t_r:
            insights.append(
                "Top 5 heurísticas por score mudou — revisar priorização e dependências de negócio."
            )
            risk_impact.append("Alteração no ranking de risco heurístico; rever quick wins.")

    out: dict[str, Any] = {
        "semantic_insights": insights,
        "semantic_insights_version": "1.1",
        "semantic_diff_sections": {
            "improved": improved,
            "worsened": worsened,
            "risk_impact": risk_impact,
        },
    }
    return out
