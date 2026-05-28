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

_INTERP_DISCLAIMER = (
    "Diff semântico v1.5: cada ligação inclui `anchoring_rationale` e `inference_strength` "
    "(`medium` apenas quando ≥2 tokens lexicais coincidem; correlação por tópico permanece `low`). "
    "Isto melhora a auditabilidade sem alegar causalidade entre mudança no modelo e incidente."
)

_LINK_TOKENS = (
    "gateway",
    "boundary",
    "trust",
    "datastore",
    "extern",
    "fluxo",
    "perimetro",
    "perímetro",
    "segment",
    "persist",
)

# Tópicos por kind de entidade — segunda ancoragem quando não há tokens lexicais em comum.
_ENTITY_TOPICS: dict[str, tuple[str, ...]] = {
    "trust_boundary": ("boundary", "trust", "perimetro", "perímetro", "segment", "segmentação", "perimeter"),
    "asset": ("ativo", "asset", "dados", "classific", "impacto"),
    "component": ("gateway", "componente", "extern", "datastore", "persist", "fluxo", "perimetro"),
}


def _change_category_from_ref(ref: str) -> str | None:
    parts = ref.split(":")
    if len(parts) >= 3 and parts[0] == "struct":
        return parts[1]
    return None


def _first_lexical_match(lines: list[str], note_tokens: set[str]) -> tuple[str, list[str]] | None:
    """Primeiro bullet com interseção de tokens; devolve (linha, tokens ordenados)."""
    for line in lines:
        inter = note_tokens & {t for t in _LINK_TOKENS if t in line.lower()}
        if inter:
            return line, sorted(inter)
    return None


def _lexical_rationale(st: list[str]) -> str:
    if len(st) >= 2:
        return f"Vários tokens em comum entre a nota da ref estrutural e o bullet ({', '.join(st)})."
    return f"Um token lexical em comum entre a nota da ref e o bullet (`{st[0]}`) — ancoragem lexical única."


def _lexical_token_link(
    r: dict[str, str], buckets: list[tuple[str, list[str]]], note_tokens: set[str]
) -> dict[str, Any] | None:
    """Primeira correspondência por tokens lexicais partilhados entre a nota da ref e um bullet."""
    ref_id = r.get("ref") or ""
    ek = r.get("entity_kind") or ""
    for section, lines in buckets:
        match = _first_lexical_match(lines, note_tokens)
        if match is None:
            continue
        line, st = match
        return {
            "structural_ref": ref_id,
            "related_section": section,
            "summary": line[:280],
            "link_kind": "lexical_token_overlap",
            "inference_strength": "medium" if len(st) >= 2 else "low",
            "anchoring_rationale": _lexical_rationale(st)[:400],
            "shared_tokens": st,
            "entity_kind": ek,
        }
    return None


def _topic_link(
    r: dict[str, str], buckets: list[tuple[str, list[str]]], topics: tuple[str, ...]
) -> dict[str, Any] | None:
    """Primeira correspondência por tópico do entity_kind ao vocabulário de um bullet."""
    ref_id = r.get("ref") or ""
    for section, lines in buckets:
        for line in lines:
            if any(t in line.lower() for t in topics):
                ek_disp = r.get("entity_kind") or "?"
                rationale = (
                    f"Alinhamento por tópico do entity_kind `{ek_disp}` ao vocabulário do bullet "
                    "(sem tokens lexicais partilhados explícitos)."
                )
                return {
                    "structural_ref": ref_id,
                    "related_section": section,
                    "summary": line[:280],
                    "link_kind": "entity_topic_correlation",
                    "inference_strength": "low",
                    "anchoring_rationale": rationale[:400],
                    "shared_tokens": [],
                    "entity_kind": r.get("entity_kind"),
                }
    return None


def _collect_lexical_links(
    refs: list[dict[str, str]], buckets: list[tuple[str, list[str]]]
) -> tuple[list[dict[str, Any]], set[str]]:
    out: list[dict[str, Any]] = []
    linked: set[str] = set()
    for r in refs:
        note_tokens = {t for t in _LINK_TOKENS if t in (r.get("note") or "").lower()}
        if not note_tokens:
            continue
        link = _lexical_token_link(r, buckets, note_tokens)
        if link is not None:
            out.append(link)
            linked.add(r.get("ref") or "")
    return out, linked


def _collect_topic_links(
    refs: list[dict[str, str]], buckets: list[tuple[str, list[str]]], linked: set[str]
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in refs:
        ref_id = r.get("ref") or ""
        if ref_id in linked:
            continue
        topics = _ENTITY_TOPICS.get((r.get("entity_kind") or "").lower(), ())
        if not topics:
            continue  # pragma: no cover - defensive guard
        link = _topic_link(r, buckets, topics)
        if link is not None:
            out.append(link)
            linked.add(ref_id)
    return out


def _interpretation_links(
    refs: list[dict[str, str]],
    insights: list[str],
    improved: list[str],
    worsened: list[str],
    risk_impact: list[str],
) -> list[dict[str, Any]]:
    """
    Ancoragem em duas camadas: (1) tokens partilhados entre nota e bullet; (2) tópico por entity_kind.

    Força inferencial: `medium` só com ≥2 tokens lexicais partilhados; caso contrário `low`.
    """
    buckets: list[tuple[str, list[str]]] = [
        ("insights", insights),
        ("improved", improved),
        ("worsened", worsened),
        ("risk_impact", risk_impact),
    ]
    lexical, linked = _collect_lexical_links(refs, buckets)
    topic = _collect_topic_links(refs, buckets, linked)
    return (lexical + topic)[:36]


def _structural_interpretation_refs(aggregate: DiffAggregate) -> list[dict[str, str]]:
    """Referências estáveis para UI/Markdown: mudança estrutural → nota interpretativa (honesta)."""

    def _row(ref: str, entity_kind: str, entity_id: str, note: str) -> dict[str, str]:
        row: dict[str, str] = {
            "ref": ref,
            "entity_kind": entity_kind,
            "entity_id": entity_id,
            "note": note,
        }
        cc = _change_category_from_ref(ref)
        if cc:
            row["change_category"] = cc
        return row

    refs: list[dict[str, str]] = []
    for cid in aggregate.components.get("added", []):
        ref = f"struct:component_added:{cid}"
        refs.append(
            _row(
                ref,
                "component",
                cid,
                "Componente novo no grafo; rever perímetro, dados e trust boundaries associados.",
            )
        )
    for cid in aggregate.components.get("removed", []):
        ref = f"struct:component_removed:{cid}"
        refs.append(
            _row(
                ref,
                "component",
                cid,
                "Componente removido; confirmar se superfícies e fluxos sensíveis foram consolidados.",
            )
        )
    for bid in aggregate.trust_boundaries.get("added", []):
        ref = f"struct:trust_boundary_added:{bid}"
        refs.append(
            _row(
                ref,
                "trust_boundary",
                bid,
                "Nova segmentação explícita; mapear fluxos que cruzam o perímetro.",
            )
        )
    for bid in aggregate.trust_boundaries.get("removed", []):
        ref = f"struct:trust_boundary_removed:{bid}"
        refs.append(
            _row(
                ref,
                "trust_boundary",
                bid,
                "Boundary removida; rede de confiança e visibilidade de ataque podem ter mudado.",
            )
        )
    for aid in aggregate.assets.get("added", []):
        ref = f"struct:asset_added:{aid}"
        refs.append(
            _row(
                ref,
                "asset",
                aid,
                "Novo ativo modelado; rever classificação, impacto e controlos.",
            )
        )
    for aid in aggregate.assets.get("removed", []):
        ref = f"struct:asset_removed:{aid}"
        refs.append(
            _row(
                ref,
                "asset",
                aid,
                "Ativo deixou de estar modelado; confirmar se o dado saiu do escopo ou ficou implícito.",
            )
        )
    return refs[:40]


def _append_quality_score_delta(
    baseline_analysis: AnalysisResult,
    revised_analysis: AnalysisResult,
    insights: list[str],
    improved: list[str],
    worsened: list[str],
) -> None:
    bq = baseline_analysis.model_quality_precheck
    rq = revised_analysis.model_quality_precheck
    if bq is None or rq is None or bq.score_0_100 == rq.score_0_100:
        return
    delta = rq.score_0_100 - bq.score_0_100
    insights.append(f"Pré-check de qualidade: score {bq.score_0_100} → {rq.score_0_100} (banda {bq.band} → {rq.band}).")
    if delta > 0:
        improved.append(f"Model quality +{delta} pts — modelo mais completo ou explícito.")
    elif delta < 0:
        worsened.append(f"Model quality {delta} pts — regressão de completude ou contexto.")


def _append_methodology_state_delta(
    baseline_analysis: AnalysisResult,
    revised_analysis: AnalysisResult,
    insights: list[str],
    improved: list[str],
    worsened: list[str],
) -> None:
    bc = baseline_analysis.methodology_completeness
    rc = revised_analysis.methodology_completeness
    if bc is None or rc is None or bc.state.value == rc.state.value:
        return
    insights.append(f"Completude metodológica: {bc.state.value} → {rc.state.value}; rever interpretação dos achados.")
    if rc.state.value == "degraded":
        worsened.append("Metodologia degrada — achados podem estar mais fracos ou genéricos.")
    else:
        improved.append("Estado metodológico alterado — alinhar leitura ao novo contexto.")


def semantic_diff_from_analyses_only(
    baseline_analysis: AnalysisResult,
    revised_analysis: AnalysisResult,
) -> tuple[list[str], list[str], list[str], list[str]]:
    """
    Secções semânticas derivadas só da comparação entre duas análises (sem diff estrutural).

    Usado no report premium com baseline de análise e para reforço de narrativa auditável.
    Heurístico — não implica causalidade entre alterações no YAML e scores.
    """
    insights: list[str] = []
    improved: list[str] = []
    worsened: list[str] = []
    risk_impact: list[str] = []

    _append_quality_score_delta(baseline_analysis, revised_analysis, insights, improved, worsened)
    _append_methodology_state_delta(baseline_analysis, revised_analysis, insights, improved, worsened)

    bs = baseline_analysis.summary.heuristic_threats_skipped_duplicate
    rs = revised_analysis.summary.heuristic_threats_skipped_duplicate
    if bs != rs:
        insights.append(f"Ruído heurístico (duplicados suprimidos): {bs} → {rs} — comparar relevância dos top risks.")

    ap_b = {h.id for h in baseline_analysis.anti_pattern_hits}
    ap_r = {h.id for h in revised_analysis.anti_pattern_hits}
    added_ap = ap_r - ap_b
    removed_ap = ap_b - ap_r
    if added_ap:
        worsened.append(
            f"Novos anti-padrões de modelagem: {', '.join(sorted(added_ap)[:5])}" + ("…" if len(added_ap) > 5 else "")
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
        insights.append("Top 5 heurísticas por score mudou — revisar priorização e dependências de negócio.")
        risk_impact.append("Alteração no ranking de risco heurístico; rever quick wins.")

    return insights, improved, worsened, risk_impact


def _classify_added_components(
    comp_add: list[str],
    revised: ThreatModelDocument,
    insights: list[str],
    risk_impact: list[str],
    worsened: list[str],
) -> None:
    """Interpreta componentes adicionados por tipo (gateway, entidade externa, datastore)."""
    r_by_id = {c.id: c for c in revised.components}
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
            insights.append(f"Novo datastore `{cid}`: rever backup, segregação e classificação de dados em repouso.")
            worsened.append("Persistência adicional — aumenta superfície de dados sensíveis.")


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

    b_by_id = {c.id: c for c in baseline.components}
    _classify_added_components(aggregate.components["added"], revised, insights, risk_impact, worsened)
    comp_rem = aggregate.components["removed"]
    for cid in comp_rem:
        c = b_by_id.get(cid)
        if c and c.kind == ComponentKind.DATASTORE:
            improved.append(f"Datastore `{cid}` removido — superfície de dados pode ter diminuído.")

    tb_add = aggregate.trust_boundaries["added"]
    for bid in tb_add:
        insights.append(f"Nova trust boundary `{bid}`: mapear fluxos que a cruzam e controlos de segmentação.")
        risk_impact.append("Segmentação de rede/perímetro mais explícita; revisar crossing flows.")
    tb_rem = aggregate.trust_boundaries["removed"]
    for bid in tb_rem:
        insights.append(f"Trust boundary `{bid}` removida: rede de confiança e superfície de ataque podem ter mudado.")
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
        ai, imp_a, wor_a, risk_a = semantic_diff_from_analyses_only(baseline_analysis, revised_analysis)
        insights.extend(ai)
        improved.extend(imp_a)
        worsened.extend(wor_a)
        risk_impact.extend(risk_a)

    structural_refs = _structural_interpretation_refs(aggregate)
    interp_links = _interpretation_links(structural_refs, insights, improved, worsened, risk_impact)

    out: dict[str, Any] = {
        "semantic_insights": insights,
        "semantic_insights_version": "1.5",
        "semantic_diff_sections": {
            "structural_change_summary": [
                f"Componentes: +{len(aggregate.components.get('added', []))} "
                f"/ −{len(aggregate.components.get('removed', []))} "
                f"/ ~{len(aggregate.components.get('changed', []))}",
                f"Trust boundaries: +{len(aggregate.trust_boundaries.get('added', []))} "
                f"/ −{len(aggregate.trust_boundaries.get('removed', []))}",
                f"Fluxos: +{len(aggregate.data_flows.get('added', []))} "
                f"/ −{len(aggregate.data_flows.get('removed', []))} "
                f"/ ~{len(aggregate.data_flows.get('changed', []))}",
            ],
            "improved": improved,
            "worsened": worsened,
            "risk_impact": risk_impact,
        },
        "semantic_structural_refs": structural_refs,
        "semantic_interpretation_links": interp_links,
        "interpretation_disclaimer": _INTERP_DISCLAIMER,
    }
    return out
