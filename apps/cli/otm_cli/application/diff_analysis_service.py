"""Use case: diff two AnalysisResult JSON files."""

from __future__ import annotations

from pathlib import Path

from otm_threat_engine import AnalysisResult
from otm_threat_engine.analysis_diff import diff_analysis_results
from otm_threat_engine.comparison_models import AnalysisDiff
from otm_threat_engine.result import HeuristicThreat, TrustBoundaryFinding

from otm_cli.application.analysis_io import load_two_analysis_results
from otm_cli.shared.enums import DiffFormat
from otm_cli.shared.errors import CliUserError

_GATE_FAILED = "threat-model gate on `diff-analysis`."

#: Share of the smaller structural shape that must reappear in the other analysis for the two to
#: count as one system. Two thirds sits inside the measured gap between different systems (<= 0.57
#: shared, they collide on catalog ids like `api`, `db`, `user`) and the same system across
#: renames, prose edits and growth (>= 0.79). See `_require_same_system`.
_MIN_SHARED_SHAPE = 2 / 3


def _pack_label(pack_id: str | None) -> str:
    return f"`{pack_id}`" if pack_id else "no pack"


def _require_same_engine_version(br: AnalysisResult, ar: AnalysisResult) -> None:
    if br.engine_version == ar.engine_version:
        return
    raise CliUserError(
        exit_code=1,
        failed=_GATE_FAILED,
        cause=(
            f"baseline was analyzed by engine {br.engine_version} and revised by {ar.engine_version}; "
            "heuristics differ between engine versions, so new/worsened threats cannot be attributed "
            "to the model change."
        ),
        next_step="re-run `otm analyze` on both models with the same engine version, then gate.",
    )


def _threat_shape(threat: HeuristicThreat) -> set[str]:
    """The modelled entities one suggested threat hangs off, tagged by kind."""
    targets = (
        ("component", threat.target_component_id),
        ("flow", threat.target_data_flow_id),
        ("asset", threat.target_asset_id),
    )
    return {f"{kind}:{entity_id}" for kind, entity_id in targets if entity_id}


def _crossing_shape(finding: TrustBoundaryFinding) -> set[str]:
    """The boundary-to-boundary edge a flow crosses.

    Ids on their own are a weak signal: the template catalog hands out `user`, `api`, `db`, so
    unrelated models overlap on a handful of them. The *wiring* — which boundary reaches which —
    is what separates them, and adding it is what widens the measured gap between the same system
    and a different one from 0.06 to 0.21.

    A finding that names no boundaries contributes nothing. An artifact written by an older
    version or edited by hand can carry one, and two unrelated models must not be read as the
    same system because they record the same *absence*.
    """
    if not (finding.from_boundary_id and finding.to_boundary_id):
        return set()
    return {f"edge:{finding.from_boundary_id}>{finding.to_boundary_id}"}


def _structural_shape(result: AnalysisResult) -> set[str]:
    """What the analysis says the modelled system *is*, independent of what it is called."""
    shape: set[str] = set()
    for threat in result.heuristic_threats:
        if not threat.skipped_as_duplicate:
            shape |= _threat_shape(threat)
    for finding in result.trust_boundary_findings:
        shape |= _crossing_shape(finding)
    return shape


def _require_same_system(br: AnalysisResult, ar: AnalysisResult) -> None:
    """Two systems, one verdict: the gate would blame a PR for the *other* model's threats.

    `report --analysis-json`, `report --baseline` and `backlog --document` already refuse a pair
    of artifacts describing different systems. `diff-analysis` is the one site of the four where a
    CI gate is actually armed, so it is the one where the wrong verdict is acted on.

    Identity used to be `document_title`, which broke on the first rename: a title is user-facing
    prose, so editing it hard-failed an armed gate — and the "different documents" error stood in
    place of the verdict, hiding any regression the same commit introduced. It is read instead
    from the shape the threats are derived from: the entities they target and the boundaries the
    flows cross. A rename leaves that untouched.

    The test is a proportion of the *smaller* shape, not equality. Adding components is the
    normal case an armed gate exists to judge and must not read as a change of system, so a
    measure that punishes growth is unusable here. Across the repository's 13 example models two
    different systems share at most 0.57 of the smaller shape, while the same model across a
    title rename, a prose edit, a doubling in size or a three-entity rename never falls below
    0.79; the quorum sits in that gap.
    """
    baseline_shape = _structural_shape(br)
    revised_shape = _structural_shape(ar)
    smaller = min(len(baseline_shape), len(revised_shape))
    if not smaller:
        # A model with no components has no shape to contradict. Refusing on no evidence would
        # be the masking bug again, so an unidentifiable pair is diffed and gated as usual.
        return
    shared = baseline_shape & revised_shape
    if len(shared) / smaller >= _MIN_SHARED_SHAPE:
        return
    raise CliUserError(
        exit_code=1,
        failed=_GATE_FAILED,
        cause=(
            f"the baseline analysis describes `{br.document_title.strip()}` and the revised one "
            f"describes `{ar.document_title.strip()}`, sharing {len(shared)} of the {smaller} "
            "structural entities the smaller one models; two different systems cannot produce a "
            "drift verdict."
        ),
        next_step="pass two analyses of the same model, or drop the gate flags to see the diff anyway.",
    )


def _require_same_industry_pack(br: AnalysisResult, ar: AnalysisResult) -> None:
    """A pack is a heuristic set, exactly like the engine version and the methodology.

    Gating a no-pack baseline against a `-p finance` revision reported 5 new CRITICAL/HIGH threats
    on an *unchanged* model — and, worse, the pack's score inflation on the baseline side masked a
    genuine risk increase, turning a build that should have failed into a green one.
    """
    if br.industry_pack_id == ar.industry_pack_id:
        return
    raise CliUserError(
        exit_code=1,
        failed=_GATE_FAILED,
        cause=(
            f"the baseline analysis was produced with {_pack_label(br.industry_pack_id)} and the revised "
            f"one with {_pack_label(ar.industry_pack_id)}; a pack adds and re-scores heuristics, so "
            "new/worsened threats cannot be attributed to the model change."
        ),
        next_step="re-run `otm analyze` on both models with the same `--pack`, then gate.",
    )


def _require_comparable_provenance(br: AnalysisResult, ar: AnalysisResult) -> None:
    """Every recorded input that shapes the heuristic set must match before a verdict is issued.

    Known gap, deliberately not faked here: a custom `--rules` file also changes the heuristic set,
    but `AnalysisResult` records no rules provenance at all, so a rules mismatch stays invisible to
    this guard. See `otm diff --rules` for the drift path that does carry rules end to end.
    """
    _require_same_engine_version(br, ar)
    _require_same_system(br, ar)
    _require_same_industry_pack(br, ar)


def run_diff_analysis(
    baseline: Path,
    revised: Path,
    *,
    fmt: DiffFormat,
    require_same_engine_version: bool = False,
) -> tuple[dict, list[str] | None, AnalysisDiff]:
    """Diff two stored analyses.

    `require_same_engine_version` is set when a CI gate is armed. It now gates on the whole
    provenance of the two artifacts, not only the engine version: comparing analyses produced
    under a different heuristic set makes that difference indistinguishable from real model drift,
    so the gate would fail (or pass) for a reason the developer did not cause. Without a gate
    armed nothing is refused — the diff itself stays informative, and answering "what does the
    finance pack add to this model?" is a legitimate use of exactly such a mismatched pair.
    """
    br, ar = load_two_analysis_results(baseline, revised)
    if require_same_engine_version:
        _require_comparable_provenance(br, ar)
    ad = diff_analysis_results(br, ar)
    payload = ad.model_dump(mode="json")
    if fmt == DiffFormat.json:
        return payload, None, ad
    lines_a: list[str] = [
        f"Methodology: {ad.methodology_before} → {ad.methodology_after}",
        f"Max score: {ad.max_risk_before} → {ad.max_risk_after} (Δ {ad.max_risk_delta!s})",
        "Active heuristics: "
        f"+{len(ad.heuristic_threats.added)} / "
        f"−{len(ad.heuristic_threats.removed)} / "
        f"~{len(ad.heuristic_threats.modified)}",
        "",
    ]
    for h in ad.heuristic_threats.added[:8]:
        lines_a.append(f"  + {h.threat_id} (score {h.score_after})")
    for h in ad.heuristic_threats.removed[:8]:
        lines_a.append(f"  − {h.threat_id}")
    for h in ad.heuristic_threats.modified[:8]:
        lines_a.append(f"  ~ {h.threat_id} Δscore={h.score_delta!s}")
    if ad.signature_remap_hints:
        lines_a.append("")
        lines_a.extend(ad.signature_remap_hints[:6])
    return payload, lines_a, ad
