"""Contratos de `merge_heuristic_threats` (persistência opcional no documento)."""

from pathlib import Path

from otm_core_schema import RiskAssessment, load_document_from_yaml_path
from otm_core_schema.enums import StrideCategory
from otm_threat_engine.merge import merge_heuristic_threats
from otm_threat_engine.result import HeuristicThreat

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def _h(
    *,
    hid: str,
    skipped: bool = False,
) -> HeuristicThreat:
    return HeuristicThreat(
        id=hid,
        title="t",
        description="d",
        stride=StrideCategory.SPOOFING,
        risk=RiskAssessment(likelihood=1, impact=1, score=1.0),
        skipped_as_duplicate=skipped,
    )


def test_merge_does_not_mutate_original_document() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    before_ids = {t.id for t in doc.threats}
    merged = merge_heuristic_threats(doc, [_h(hid="eng_new_merge_1")])
    assert {t.id for t in doc.threats} == before_ids
    assert any(t.id == "eng_new_merge_1" for t in merged.threats)


def test_merge_only_new_skips_skipped_heuristics() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    merged = merge_heuristic_threats(
        doc,
        [_h(hid="skip_me", skipped=True), _h(hid="keep_me", skipped=False)],
        only_new=True,
    )
    assert not any(t.id == "skip_me" for t in merged.threats)
    assert any(t.id == "keep_me" for t in merged.threats)


def test_merge_only_new_false_includes_skipped_when_id_unique() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    merged = merge_heuristic_threats(
        doc,
        [_h(hid="was_skipped", skipped=True)],
        only_new=False,
    )
    assert any(t.id == "was_skipped" for t in merged.threats)


def test_merge_skips_when_heuristic_id_already_in_document() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    doc2 = merge_heuristic_threats(doc, [_h(hid="eng_dup")])
    merged = merge_heuristic_threats(doc2, [_h(hid="eng_dup")])
    assert sum(1 for t in merged.threats if t.id == "eng_dup") == 1


def test_merge_threat_metadata_marks_engine_source() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    merged = merge_heuristic_threats(doc, [_h(hid="eng_meta_check")])
    t = next(x for x in merged.threats if x.id == "eng_meta_check")
    assert t.metadata.get("source") == "otm_threat_engine"
    assert t.metadata.get("engine_heuristic") is True


def test_merge_dedupes_duplicate_heuristic_ids_in_same_batch() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    merged = merge_heuristic_threats(
        doc,
        [_h(hid="eng_batch_dup"), _h(hid="eng_batch_dup")],
    )
    assert sum(1 for t in merged.threats if t.id == "eng_batch_dup") == 1
