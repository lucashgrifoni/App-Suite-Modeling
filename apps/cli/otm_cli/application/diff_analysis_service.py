"""Use case: diff two AnalysisResult JSON files."""

from __future__ import annotations

from pathlib import Path

from otm_threat_engine.analysis_diff import diff_analysis_results

from otm_cli.application.analysis_io import load_two_analysis_results
from otm_cli.shared.enums import DiffFormat


def run_diff_analysis(
    baseline: Path,
    revised: Path,
    *,
    fmt: DiffFormat,
) -> tuple[dict, list[str] | None]:
    br, ar = load_two_analysis_results(baseline, revised)
    ad = diff_analysis_results(br, ar)
    payload = ad.model_dump(mode="json")
    if fmt == DiffFormat.json:
        return payload, None
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
    return payload, lines_a
