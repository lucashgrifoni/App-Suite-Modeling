"""Catálogo STRIDE → frameworks e integração com o motor."""

from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_core_schema.enums import StrideCategory
from otm_framework_mappings import (
    FrameworkCatalog,
    default_stride_registry,
    framework_display_name,
    load_packaged_stride_map,
)
from otm_threat_engine import analyze_document, merge_heuristic_threats

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_packaged_stride_map_loads_and_covers_all_stride() -> None:
    reg = load_packaged_stride_map()
    for sc in StrideCategory:
        refs = reg.refs_for_stride(sc)
        assert len(refs) >= 4, f"{sc.value} deve ter refs dos quatro pilares MVP"
    fw_ids = {r.framework for r in reg.refs_for_stride(StrideCategory.SPOOFING)}
    assert FrameworkCatalog.OWASP_TM.value in fw_ids
    assert FrameworkCatalog.OWASP_ASVS.value in fw_ids
    assert FrameworkCatalog.NIST_CSF.value in fw_ids
    assert FrameworkCatalog.ISO_27001.value in fw_ids


def test_default_registry_is_cached() -> None:
    assert default_stride_registry() is default_stride_registry()


def test_framework_display_name_known() -> None:
    assert "ASVS" in framework_display_name("owasp_asvs")


def test_analyze_attaches_framework_refs_and_summary_counts() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = analyze_document(doc)
    active = [h for h in r.heuristic_threats if not h.skipped_as_duplicate]
    assert active
    for h in active:
        assert h.framework_refs, h.id
    assert r.summary.framework_ref_counts_by_catalog
    total = sum(r.summary.framework_ref_counts_by_catalog.values())
    assert total == sum(len(h.framework_refs) for h in r.heuristic_threats)


def test_merge_copies_framework_refs_to_threat() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    r = analyze_document(doc)
    merged = merge_heuristic_threats(doc, r.heuristic_threats)
    by_id = {t.id: t for t in merged.threats}
    for h in r.heuristic_threats:
        if h.skipped_as_duplicate:
            continue
        t = by_id.get(h.id)
        assert t is not None
        assert t.framework_refs == h.framework_refs
