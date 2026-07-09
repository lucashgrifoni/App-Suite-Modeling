"""P1 evolution — PLOT4ai heuristics carry OWASP LLM Top 10 (2025) + MITRE ATLAS refs.

The AI lens gains standard traceability the same way STRIDE threats did in P0:
a data-driven per-heuristic map (`ai_heuristic_framework_map.yaml`) flows through
the existing `framework_refs` enrichment. AI refs are *additive* — a PLOT4ai
threat keeps its STRIDE-category CAPEC/CWE refs and gains the AI-specific ones.
No schema/contract change.
"""

from __future__ import annotations

import re
from pathlib import Path

from otm_core_schema import ThreatModelMethodology, load_document_from_yaml_path
from otm_framework_mappings.ai_heuristic_registry import default_ai_heuristic_registry
from otm_threat_engine import analyze_document

_LLM_EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "plot4ai-calibration" / "otm-ai-001-llm-chat.otm.yaml"

# Official OWASP LLM Top 10 2025 identifiers (LLM01:2025 .. LLM10:2025) and the
# three verified MITRE ATLAS technique ids used by the map.
_OWASP_LLM_RE = re.compile(r"^LLM(0[1-9]|10):2025$")
_ATLAS_RE = re.compile(r"^AML\.T\d{4}$")
_VERIFIED_ATLAS = {"AML.T0051", "AML.T0024", "AML.T0034"}


def test_ai_map_shape_is_valid_and_ids_are_wellformed() -> None:
    reg = default_ai_heuristic_registry()
    # Every mapped heuristic id is a plot4ai_* id with at least one OWASP LLM ref.
    mapped = reg._by_heuristic  # noqa: SLF001 - test asserts packaged data shape
    assert mapped, "AI heuristic map must not be empty"
    for hid, refs in mapped.items():
        assert hid.startswith("plot4ai_"), f"unexpected heuristic id in AI map: {hid}"
        frameworks = {r.framework for r in refs}
        assert "owasp_llm" in frameworks, f"{hid} missing an OWASP LLM ref"
        for r in refs:
            if r.framework == "owasp_llm":
                assert _OWASP_LLM_RE.match(r.control_id), f"{hid}: bad OWASP LLM id {r.control_id}"
            elif r.framework == "mitre_atlas":
                assert _ATLAS_RE.match(r.control_id), f"{hid}: bad ATLAS id {r.control_id}"
                assert r.control_id in _VERIFIED_ATLAS, f"{hid}: unverified ATLAS id {r.control_id}"
            else:  # pragma: no cover - map only carries AI frameworks
                raise AssertionError(f"{hid}: unexpected framework {r.framework} in AI map")


def test_atlas_notes_use_current_canonical_technique_names() -> None:
    """Regression: AML.T0024 shipped as 'Exfiltration via ML Inference API'.

    MITRE ATLAS renamed several techniques from 'ML' to 'AI'; per the canonical
    `mitre-atlas/atlas-data` (dist/ATLAS.yaml), AML.T0024 is 'Exfiltration via AI
    Inference API'. The note is a user-facing factual claim, so guard the rename.
    """
    reg = default_ai_heuristic_registry()
    expected_names = {
        "AML.T0051": "LLM Prompt Injection",
        "AML.T0024": "Exfiltration via AI Inference API",
        "AML.T0034": "Cost Harvesting",
    }
    seen: set[str] = set()
    for refs in reg._by_heuristic.values():  # noqa: SLF001 - test asserts packaged data shape
        for r in refs:
            if r.framework != "mitre_atlas":
                continue
            seen.add(r.control_id)
            note = r.notes or ""
            want = expected_names[r.control_id]
            assert want in note, f"{r.control_id}: note must name it '{want}'"
            assert "ML Inference API" not in note, f"{r.control_id}: stale pre-rename ATLAS name"
    assert seen == set(expected_names), f"ATLAS ids in map ({seen}) drifted from the verified set"


def test_plot4ai_threats_carry_owasp_llm_refs_additively() -> None:
    doc = load_document_from_yaml_path(_LLM_EXAMPLE)
    result = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    reg = default_ai_heuristic_registry()

    plot4ai = [h for h in result.heuristic_threats if h.id.startswith("plot4ai_")]
    assert plot4ai, "LLM example must yield PLOT4ai heuristics"

    checked = 0
    for h in plot4ai:
        expected = {r.control_id for r in reg.refs_for_heuristic(h.id) if r.framework == "owasp_llm"}
        if not expected:
            continue  # a plot4ai id not (yet) in the AI map — still valid
        checked += 1
        catalogs = {r.framework for r in h.framework_refs}
        got_llm = {r.control_id for r in h.framework_refs if r.framework == "owasp_llm"}
        assert expected <= got_llm, f"{h.id}: expected OWASP LLM {expected}, got {got_llm}"
        # Additivity: STRIDE-category CAPEC/CWE refs are preserved, not replaced.
        assert "capec" in catalogs and "cwe" in catalogs, f"{h.id}: lost STRIDE CAPEC/CWE refs"
    assert checked >= 3, "expected several mapped PLOT4ai heuristics on the LLM example"


def test_summary_counts_include_ai_catalogs() -> None:
    doc = load_document_from_yaml_path(_LLM_EXAMPLE)
    result = analyze_document(doc, methodology=ThreatModelMethodology.PLOT4AI)
    counts = result.summary.framework_ref_counts_by_catalog
    assert counts.get("owasp_llm", 0) > 0
    assert counts.get("mitre_atlas", 0) > 0
    # AI refs did not displace the STRIDE catalogs.
    assert counts.get("capec", 0) > 0 and counts.get("cwe", 0) > 0
