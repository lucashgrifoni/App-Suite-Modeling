"""Integração de industry packs no motor (risco + ameaças extra)."""

from __future__ import annotations

from otm_core_schema import Component, ThreatModelDocument
from otm_industry_packs.models import AdditionalThreatRule, PackDefinition

from otm_threat_engine.result import HeuristicThreat
from otm_threat_engine.risk_calc import build_risk_assessment


def apply_pack_to_li(
    likelihood: int,
    impact: int,
    pack: PackDefinition | None,
) -> tuple[int, int]:
    """Aplica multiplicadores do pack e mantém L,I em [1,5]."""
    if pack is None or pack.risk_tuning is None:
        return likelihood, impact
    rt = pack.risk_tuning
    l2 = min(5, max(1, round(likelihood * rt.likelihood_multiplier)))
    i2 = min(5, max(1, round(impact * rt.impact_multiplier)))
    return l2, i2


def _rule_matches_component(rule: AdditionalThreatRule, comp: Component) -> bool:
    if not rule.target_component_kinds:
        return True
    return comp.kind in rule.target_component_kinds


def _clamp_li(value: int) -> int:
    return min(5, max(1, value))


def _base_li_from_rule(rule: AdditionalThreatRule) -> tuple[int, int]:
    return _clamp_li(3 + rule.likelihood_delta), _clamp_li(3 + rule.impact_delta)


def _build_pack_heuristic(
    *,
    pack: PackDefinition,
    rule: AdditionalThreatRule,
    component_id: str,
    hid: str,
    skipped_as_duplicate: bool,
) -> HeuristicThreat:
    base_l, base_i = _base_li_from_rule(rule)
    bl, bi = apply_pack_to_li(base_l, base_i, pack)
    risk = build_risk_assessment(bl, bi)
    desc = rule.description or (f"Ameaça contextual do setor ({pack.name}). Rever control_hints do pack.")
    return HeuristicThreat(
        id=hid,
        title=f"[pack:{pack.id}] {rule.title}",
        description=desc,
        stride=rule.stride,
        target_component_id=component_id,
        risk=risk,
        skipped_as_duplicate=skipped_as_duplicate,
    )


def iter_pack_heuristic_threats(
    doc: ThreatModelDocument,
    pack: PackDefinition,
    covered_keys: set[tuple[str | None, str | None, str]],
) -> tuple[list[HeuristicThreat], int]:
    """
    Ameaças adicionais do pack. `covered_keys` inclui ameaças do documento e
    heurísticas base já aceites (não duplicadas).
    """
    out: list[HeuristicThreat] = []
    skipped = 0
    emitted_pack_keys: set[tuple[str, str, str]] = set()

    for comp in doc.components:
        for rule in pack.additional_threats:
            if not _rule_matches_component(rule, comp):
                continue
            stride_key = rule.stride.value
            doc_style_key = (comp.id, None, stride_key)
            pack_unique = (comp.id, rule.id, stride_key)
            if pack_unique in emitted_pack_keys:
                continue
            hid = f"pack_{pack.id}_{rule.id}_{comp.id}"

            if doc_style_key in covered_keys:
                out.append(
                    _build_pack_heuristic(
                        pack=pack,
                        rule=rule,
                        component_id=comp.id,
                        hid=hid,
                        skipped_as_duplicate=True,
                    )
                )
                skipped += 1
                continue

            emitted_pack_keys.add(pack_unique)
            covered_keys.add(doc_style_key)
            out.append(
                _build_pack_heuristic(
                    pack=pack,
                    rule=rule,
                    component_id=comp.id,
                    hid=hid,
                    skipped_as_duplicate=False,
                )
            )
    return out, skipped
