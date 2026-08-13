"""Use case: diff two AnalysisResult JSON files."""

from __future__ import annotations

from pathlib import Path

from otm_threat_engine import AnalysisResult
from otm_threat_engine.analysis_diff import diff_analysis_results
from otm_threat_engine.analysis_identity import system_overlap
from otm_threat_engine.comparison_models import AnalysisDiff

from otm_cli.application.analysis_io import load_two_analysis_results
from otm_cli.shared.enums import DiffFormat
from otm_cli.shared.errors import CliUserError

_GATE_FAILED = "threat-model gate on `diff-analysis`."


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


def _require_same_system(br: AnalysisResult, ar: AnalysisResult) -> None:
    """Two systems, one verdict: the gate would blame a PR for the *other* model's threats.

    `report --analysis-json`, `report --baseline` and `backlog --document` refuse mismatched
    pairs too. `diff-analysis` is the one site of the four where a CI gate is actually armed, so
    it is the one where the wrong verdict is acted on.

    Identity used to be `document_title`, which broke on the first rename: a title is user-facing
    prose, so editing it hard-failed an armed gate — and the "different documents" error stood in
    place of the verdict, hiding any regression the same commit introduced. It is read instead
    from the shape the threats are derived from (`otm_threat_engine.analysis_identity`, the same
    module every other pairing guard now reads identity from). A rename leaves that untouched.
    """
    overlap = system_overlap(br, ar)
    if overlap.is_same_system:
        return
    raise CliUserError(
        exit_code=1,
        failed=_GATE_FAILED,
        cause=(
            f"the baseline analysis describes `{br.document_title.strip()}` and the revised one "
            f"describes `{ar.document_title.strip()}`, sharing {overlap.shared} of the {overlap.smaller} "
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
