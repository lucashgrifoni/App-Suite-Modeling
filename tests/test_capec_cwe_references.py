"""P0 evolution — generated threats carry CAPEC/CWE references for traceability.

Threat-modeling-as-code is more authoritative when each suggested STRIDE threat
links to the standard attack-pattern (MITRE CAPEC) and weakness (MITRE CWE)
taxonomies. These flow through the existing `framework_refs` enrichment from the
data-driven STRIDE map, so no schema/contract change is required.
"""

from __future__ import annotations

from pathlib import Path

from otm_core_schema import StrideCategory, load_document_from_yaml_path
from otm_framework_mappings.registry import default_stride_registry
from otm_threat_engine import analyze_document

_MINIMAL = Path(__file__).resolve().parents[1] / "examples" / "minimal.otm.yaml"

_STRIDE = [
    StrideCategory.SPOOFING,
    StrideCategory.TAMPERING,
    StrideCategory.REPUDIATION,
    StrideCategory.INFORMATION_DISCLOSURE,
    StrideCategory.DENIAL_OF_SERVICE,
    StrideCategory.ELEVATION_OF_PRIVILEGE,
]


def test_registry_maps_capec_and_cwe_for_every_stride_category() -> None:
    reg = default_stride_registry()
    for cat in _STRIDE:
        refs = reg.refs_for_stride(cat)
        by_fw = {r.framework: r for r in refs}
        assert "capec" in by_fw, f"missing CAPEC ref for {cat.value}"
        assert "cwe" in by_fw, f"missing CWE ref for {cat.value}"
        assert by_fw["capec"].control_id.startswith("CAPEC-")
        assert by_fw["cwe"].control_id.startswith("CWE-")


def test_analysis_threats_carry_capec_and_cwe_refs() -> None:
    result = analyze_document(load_document_from_yaml_path(_MINIMAL))
    engine_threats = [h for h in result.heuristic_threats if h.id.startswith("eng_")]
    assert engine_threats
    sample = engine_threats[0]
    catalogs = {r.framework for r in sample.framework_refs}
    assert "capec" in catalogs and "cwe" in catalogs

    counts = result.summary.framework_ref_counts_by_catalog
    assert counts.get("capec", 0) > 0
    assert counts.get("cwe", 0) > 0
