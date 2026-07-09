"""Use case: diff two AnalysisResult JSON files."""

from __future__ import annotations

from pathlib import Path

from otm_threat_engine.analysis_diff import diff_analysis_results
from otm_threat_engine.comparison_models import AnalysisDiff

from otm_cli.application.analysis_io import load_two_analysis_results
from otm_cli.shared.enums import DiffFormat
from otm_cli.shared.errors import CliUserError


def run_diff_analysis(
    baseline: Path,
    revised: Path,
    *,
    fmt: DiffFormat,
    require_same_engine_version: bool = False,
) -> tuple[dict, list[str] | None, AnalysisDiff]:
    """Diff two stored analyses.

    `require_same_engine_version` is set when a CI gate is armed: comparing analyses produced by
    different engine versions makes heuristic churn indistinguishable from real model drift, so
    the gate would fail (or pass) for a reason the developer did not cause.
    """
    br, ar = load_two_analysis_results(baseline, revised)
    if require_same_engine_version and br.engine_version != ar.engine_version:
        raise CliUserError(
            exit_code=1,
            failed="threat-model gate on `diff-analysis`.",
            cause=(
                f"baseline was analyzed by engine {br.engine_version} and revised by {ar.engine_version}; "
                "heuristics differ between engine versions, so new/worsened threats cannot be attributed "
                "to the model change."
            ),
            next_step="re-run `otm analyze` on both models with the same engine version, then gate.",
        )
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
