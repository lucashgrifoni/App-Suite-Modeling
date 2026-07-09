"""Diff entre dois `AnalysisResult` — sem I/O."""

from __future__ import annotations

import json
from typing import Any

from otm_core_schema.diff import FieldChange

from otm_threat_engine.comparison_models import (
    AnalysisDiff,
    FrameworkRefCountDelta,
    HeuristicThreatDelta,
    HeuristicThreatDeltaSection,
    MethodologyInsightsDelta,
    PackHintsDelta,
    StructuralFindingDelta,
    TrustBoundaryFindingDelta,
)
from otm_threat_engine.result import AnalysisResult, HeuristicThreat


def _json_key(v: Any) -> str:
    return json.dumps(v, sort_keys=True, default=str)


def _finding_key(code: str, data_flow_id: str | None) -> str:
    return f"{code}|{data_flow_id or ''}"


def _heuristic_signature(h: HeuristicThreat) -> tuple[Any, ...]:
    return (
        h.stride.value,
        h.target_component_id or "",
        h.target_data_flow_id or "",
        h.target_asset_id or "",
        (h.title or "").strip().lower()[:120],
    )


def _active_heuristics(result: AnalysisResult) -> dict[str, HeuristicThreat]:
    return {h.id: h for h in result.heuristic_threats if not h.skipped_as_duplicate}


def _field_changes_heuristic(before: HeuristicThreat, after: HeuristicThreat) -> list[FieldChange]:
    bd = before.model_dump(mode="json")
    ad = after.model_dump(mode="json")
    keys = set(bd) | set(ad)
    skip = {"id"}
    out: list[FieldChange] = []
    for k in sorted(keys):
        if k in skip:
            continue
        if k == "framework_refs":
            if _json_key(bd.get("framework_refs")) != _json_key(ad.get("framework_refs")):
                out.append(
                    FieldChange(
                        field="framework_refs",
                        before=bd.get("framework_refs"),
                        after=ad.get("framework_refs"),
                    )
                )
            continue
        if _json_key(bd.get(k)) != _json_key(ad.get(k)):
            out.append(FieldChange(field=k, before=bd.get(k), after=ad.get(k)))
    return out


def _methodology_insights_delta(baseline: AnalysisResult, revised: AnalysisResult) -> MethodologyInsightsDelta | None:
    bi = baseline.methodology_insights
    ai = revised.methodology_insights
    if not (bi or ai):
        return None
    keys_b = {b.key for b in (bi.blocks if bi else [])}
    keys_a = {b.key for b in (ai.blocks if ai else [])}
    return MethodologyInsightsDelta(
        profile_before=bi.profile if bi else None,
        profile_after=ai.profile if ai else None,
        blocks_added=sorted(keys_a - keys_b),
        blocks_removed=sorted(keys_b - keys_a),
    )


def _pair_signature_remaps(
    b_act: dict[str, HeuristicThreat],
    a_act: dict[str, HeuristicThreat],
    *,
    added_ids: list[str],
    removed_ids: list[str],
) -> dict[str, str]:
    """1:1 pairing `added_id -> removed_id` for threats that only changed id.

    Two entities are the same threat when their signature (stride, targets, title) matches.
    Pairing is one-to-one and deterministic: ids are iterated in sorted order and a removed
    id, once claimed, cannot be claimed again. The signature deliberately excludes the score,
    so a paired threat may still have *worsened* — callers must compare scores rather than
    assume a remap is a no-op.
    """
    rem_by_sig: dict[tuple[Any, ...], list[str]] = {}
    for hid in removed_ids:
        rem_by_sig.setdefault(_heuristic_signature(b_act[hid]), []).append(hid)

    pairs: dict[str, str] = {}
    for hid in added_ids:
        bucket = rem_by_sig.get(_heuristic_signature(a_act[hid]))
        if bucket:
            pairs[hid] = bucket.pop(0)
    return pairs


def _build_heuristic_section(
    b_act: dict[str, HeuristicThreat],
    a_act: dict[str, HeuristicThreat],
    *,
    added_ids: list[str],
    removed_ids: list[str],
    common: set[str],
    remap_pairs: dict[str, str],
) -> HeuristicThreatDeltaSection:
    section = HeuristicThreatDeltaSection()
    removed_to_added = {removed: added for added, removed in remap_pairs.items()}

    for hid in added_ids:
        paired = remap_pairs.get(hid)
        after = a_act[hid].risk.score
        if paired is None:
            section.added.append(HeuristicThreatDelta(threat_id=hid, change="added", score_after=after))
            continue
        # Same threat, new id. Carry the baseline score so consumers (e.g. the CI gate) can
        # tell an inert rename from a rename that also raised the risk.
        before = b_act[paired].risk.score
        delta = None if before is None or after is None else float(after) - float(before)
        section.added.append(
            HeuristicThreatDelta(
                threat_id=hid,
                change="added",
                match_kind="signature_remap",
                paired_id=paired,
                score_before=before,
                score_after=after,
                score_delta=delta,
            )
        )

    for hid in removed_ids:
        paired_add = removed_to_added.get(hid)
        section.removed.append(
            HeuristicThreatDelta(
                threat_id=hid,
                change="removed",
                match_kind="signature_remap" if paired_add else "id",
                paired_id=paired_add,
                score_before=b_act[hid].risk.score,
            )
        )

    for hid in sorted(common):
        ch = _field_changes_heuristic(b_act[hid], a_act[hid])
        if not ch:
            continue
        sb = b_act[hid].risk.score
        sa = a_act[hid].risk.score
        sd = None if sb is None or sa is None else float(sa) - float(sb)
        section.modified.append(
            HeuristicThreatDelta(
                threat_id=hid,
                change="modified",
                score_before=sb,
                score_after=sa,
                score_delta=sd,
                field_changes=ch,
            )
        )
    return section


def _signature_remap_hints(remap_pairs: dict[str, str]) -> list[str]:
    """Human-readable hints, derived from the same 1:1 pairing the deltas carry."""
    return [
        f"Possível remapeamento de heurística: baseline `{removed}` → revisão `{added}` "
        f"(mesma assinatura: stride/alvos/título)."
        for added, removed in remap_pairs.items()
    ]


def diff_analysis_results(baseline: AnalysisResult, revised: AnalysisResult) -> AnalysisDiff:
    """
    Compara dois resultados de análise.

    Regra de matching: **id** para added/removed/modified.
    **Assinatura** só gera `signature_remap_hints` (não funde entidades).
    """
    meth_b = baseline.methodology.value
    meth_a = revised.methodology.value
    meth_changed = meth_b != meth_a

    b_act = _active_heuristics(baseline)
    a_act = _active_heuristics(revised)
    b_ids = set(b_act)
    a_ids = set(a_act)

    added_ids = sorted(a_ids - b_ids)
    removed_ids = sorted(b_ids - a_ids)
    common = b_ids & a_ids

    max_b = baseline.summary.max_risk_score
    max_a = revised.summary.max_risk_score
    max_delta = None
    if max_b is not None or max_a is not None:
        max_delta = float(max_a or 0.0) - float(max_b or 0.0)

    remap_pairs = _pair_signature_remaps(b_act, a_act, added_ids=added_ids, removed_ids=removed_ids)
    section = _build_heuristic_section(
        b_act, a_act, added_ids=added_ids, removed_ids=removed_ids, common=common, remap_pairs=remap_pairs
    )
    hints = _signature_remap_hints(remap_pairs)

    cats_b = baseline.summary.framework_ref_counts_by_catalog
    cats_a = revised.summary.framework_ref_counts_by_catalog
    fw_delta: list[FrameworkRefCountDelta] = []
    for cat in sorted(set(cats_b) | set(cats_a)):
        cb = cats_b.get(cat, 0)
        ca = cats_a.get(cat, 0)
        if cb != ca:
            fw_delta.append(FrameworkRefCountDelta(catalog=cat, count_before=cb, count_after=ca))

    hints_b = baseline.pack_control_hints
    hints_a = revised.pack_control_hints
    set_b = set(hints_b)
    set_a = set(hints_a)
    pack_delta = PackHintsDelta(
        added=sorted(set_a - set_b),
        removed=sorted(set_b - set_a),
    )

    ins_delta = _methodology_insights_delta(baseline, revised)

    keys_b_f = {_finding_key(f.code, f.data_flow_id) for f in baseline.trust_boundary_findings}
    keys_a_f = {_finding_key(f.code, f.data_flow_id) for f in revised.trust_boundary_findings}
    tb_delta = TrustBoundaryFindingDelta(
        added_keys=sorted(keys_a_f - keys_b_f),
        removed_keys=sorted(keys_b_f - keys_a_f),
        count_before=len(baseline.trust_boundary_findings),
        count_after=len(revised.trust_boundary_findings),
    )

    codes_b = {f.code for f in baseline.structural_findings}
    codes_a = {f.code for f in revised.structural_findings}
    sf_delta = StructuralFindingDelta(
        codes_added=sorted(codes_a - codes_b),
        codes_removed=sorted(codes_b - codes_a),
        count_before=len(baseline.structural_findings),
        count_after=len(revised.structural_findings),
    )

    return AnalysisDiff(
        methodology_before=meth_b,
        methodology_after=meth_a,
        methodology_changed=meth_changed,
        max_risk_before=max_b,
        max_risk_after=max_a,
        max_risk_delta=max_delta,
        heuristic_threats=section,
        framework_ref_counts=fw_delta,
        pack_control_hints=pack_delta,
        methodology_insights=ins_delta,
        trust_boundary_findings=tb_delta,
        structural_findings=sf_delta,
        signature_remap_hints=hints,
    )
