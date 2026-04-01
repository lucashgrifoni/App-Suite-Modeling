"""
Explicabilidade curta para comparação de modelos (diff + delta de análise).

Evita repetir toda a lista `key_insights`; extrai 1–6 factos priorizados e contextualizados.
"""

from __future__ import annotations

from otm_explainability import (
    ExplanationCategory,
    ExplanationRecord,
    ExplanationType,
    RelatedEntityRef,
    explanation_id,
)

from otm_threat_engine.comparison_models import DiffAggregate, ThreatModelComparisonResult


def _structural_headline(agg: DiffAggregate) -> tuple[str, str, list[str]] | None:
    """Retorna (rótulo interno, mensagem, evidências curtas) da maior mudança estrutural."""
    best: tuple[int, str, str, list[str]] | None = None
    sections: list[tuple[str, str, dict[str, list[str]]]] = [
        ("componentes", "Componentes", agg.components),
        ("ativos", "Ativos", agg.assets),
        ("fluxos", "Fluxos de dados", agg.data_flows),
        ("fronteiras", "Fronteiras de confiança", agg.trust_boundaries),
    ]
    for key, label, block in sections:
        added = block.get("added", [])
        removed = block.get("removed", [])
        changed = block.get("changed", [])
        n = len(added) + len(removed) + len(changed)
        if n <= 0:
            continue
        ev = [
            f"+{len(added)} adicionados",
            f"−{len(removed)} removidos",
            f"~{len(changed)} alterados",
        ]
        if key == "fluxos" and added[:2]:
            ev.append(f"ex.: novos fluxos `{added[0]}`" + (f", `{added[1]}`" if len(added) > 1 else ""))
        if best is None or n > best[0]:
            msg = (
                f"A maior alteração estrutural está em {label.lower()}: "
                f"{len(added)} novos, {len(removed)} removidos, {len(changed)} modificados."
            )
            best = (n, key, msg, ev)
    if best is None:
        return None
    return best[1], best[2], best[3]


def build_comparison_explanations(result: ThreatModelComparisonResult) -> list[ExplanationRecord]:
    """Gera poucos `ExplanationRecord` acionáveis; não duplica texto longo dos relatórios."""
    out: list[ExplanationRecord] = []
    n = 0

    def take() -> int:
        nonlocal n
        n += 1
        return n

    sh = _structural_headline(result.aggregate)
    if sh:
        _key, msg, ev = sh
        out.append(
            ExplanationRecord(
                id=explanation_id(take(), prefix="exp_cmp"),
                type=ExplanationType.DIFF_CHANGE,
                category=ExplanationCategory.DIFF,
                subject="Mudança estrutural principal",
                message=msg,
                evidence=ev,
                confidence="high",
                related_entities=[
                    RelatedEntityRef(entity_kind="comparison", entity_id="structural_delta"),
                ],
            )
        )

    ad = result.analysis
    if ad and ad.methodology_changed:
        out.append(
            ExplanationRecord(
                id=explanation_id(take(), prefix="exp_cmp"),
                type=ExplanationType.AGGREGATION,
                category=ExplanationCategory.METHODOLOGY,
                subject="Metodologia da análise",
                message=(
                    f"As análises foram produzidas com metodologias diferentes "
                    f"({ad.methodology_before} → {ad.methodology_after}); "
                    "compare achados sempre neste enquadramento."
                ),
                evidence=[
                    f"baseline: {ad.methodology_before}",
                    f"revisão: {ad.methodology_after}",
                ],
                confidence="high",
                related_entities=[RelatedEntityRef(entity_kind="analysis_diff", entity_id="methodology")],
            )
        )

    rd = result.risk_delta
    if rd.analysis_max_score_delta is not None and abs(rd.analysis_max_score_delta) >= 0.5:
        up = rd.analysis_max_score_delta > 0
        out.append(
            ExplanationRecord(
                id=explanation_id(take(), prefix="exp_cmp"),
                type=ExplanationType.RISK_SCORE,
                category=ExplanationCategory.RISK,
                subject="Risco agregado (score máximo)",
                message=(
                    f"O score máximo entre heurísticas ativas {'subiu' if up else 'desceu'} "
                    f"(Δ {rd.analysis_max_score_delta:+.1f}): "
                    f"{rd.analysis_max_score_baseline} → {rd.analysis_max_score_revised}."
                ),
                evidence=["Δ calculado entre resultados de `analyze` em ambos os lados."],
                confidence="medium",
                related_entities=[RelatedEntityRef(entity_kind="analysis_diff", entity_id="max_risk")],
            )
        )

    if result.key_insights:
        head = result.key_insights[0]
        if not any(e.message == head for e in out):
            extra_ev = list(result.key_insights[1:3]) if len(result.key_insights) > 1 else []
            out.append(
                ExplanationRecord(
                    id=explanation_id(take(), prefix="exp_cmp"),
                    type=ExplanationType.AGGREGATION,
                    category=ExplanationCategory.DIFF,
                    subject="Síntese comparativa",
                    message=head[:500],
                    evidence=extra_ev,
                    confidence="medium",
                    related_entities=[
                        RelatedEntityRef(entity_kind="comparison", entity_id="key_insight"),
                    ],
                )
            )

    if not out and result.structural_insights:
        extra_ev = list(result.structural_insights[1:3])
        out.append(
            ExplanationRecord(
                id=explanation_id(take(), prefix="exp_cmp"),
                type=ExplanationType.DIFF_CHANGE,
                category=ExplanationCategory.DIFF,
                subject="Alteração estrutural",
                message=result.structural_insights[0][:500],
                evidence=extra_ev,
                confidence="high",
                related_entities=[
                    RelatedEntityRef(entity_kind="comparison", entity_id="structural_insight"),
                ],
            )
        )
    if not out and result.summary.headline:
        out.append(
            ExplanationRecord(
                id=explanation_id(take(), prefix="exp_cmp"),
                type=ExplanationType.DIFF_CHANGE,
                category=ExplanationCategory.DIFF,
                subject="Resumo do diff",
                message=result.summary.headline[:500],
                evidence=[],
                confidence="medium",
                related_entities=[
                    RelatedEntityRef(entity_kind="comparison", entity_id="headline"),
                ],
            )
        )

    return out[:8]
