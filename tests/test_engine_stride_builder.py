from pathlib import Path

from otm_core_schema import Threat, TreatmentStatus, load_document_from_yaml_path
from otm_core_schema.enums import StrideCategory
from otm_threat_engine.engine_stride_builder import (
    append_component_heuristics,
    append_flow_heuristics,
)
from otm_threat_engine.engine_support import cross_boundary_flow_ids, existing_threat_keys

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_append_component_heuristics_produces_entries() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    out = []
    skipped = append_component_heuristics(
        doc=doc,
        heuristics=out,
        existing=existing_threat_keys(doc),
        assets_by_id={a.id: a for a in doc.assets},
        pack=None,
    )
    assert out
    assert skipped >= 0


def test_append_flow_heuristics_produces_entries() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    out = []
    skipped = append_flow_heuristics(
        doc=doc,
        heuristics=out,
        existing=existing_threat_keys(doc),
        cross_flows=cross_boundary_flow_ids(doc),
        pack=None,
    )
    assert out
    assert skipped >= 0


def test_append_flow_heuristics_dedupes_tampering_when_cross_and_unencrypted() -> None:
    """
    Cruzamento de fronteira introduz TAMPERING; fluxo não encriptado também.
    Deve haver só uma heurística TAMPERING por fluxo (vista ativa).
    """
    doc = load_document_from_yaml_path(_MINIMAL)
    flows = [f.model_copy(update={"encrypted": False}) if f.id == "http_in" else f for f in doc.data_flows]
    doc2 = doc.model_copy(update={"data_flows": flows})
    out: list = []
    append_flow_heuristics(
        doc=doc2,
        heuristics=out,
        existing=existing_threat_keys(doc2),
        cross_flows=cross_boundary_flow_ids(doc2),
        pack=None,
    )
    http = [h for h in out if h.target_data_flow_id == "http_in" and not h.skipped_as_duplicate]
    strides = [h.stride for h in http]
    assert strides.count(StrideCategory.TAMPERING) == 1
    assert StrideCategory.INFORMATION_DISCLOSURE in strides


def test_append_component_heuristics_marks_duplicate_when_document_covers_key() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    comp0 = doc.components[0]
    stride0 = StrideCategory.SPOOFING
    doc2 = doc.model_copy(
        update={
            "threats": [
                Threat(
                    id="manual",
                    title="cover",
                    stride=stride0,
                    target_component_id=comp0.id,
                    treatment_status=TreatmentStatus.NEW,
                ),
            ]
        }
    )
    existing = existing_threat_keys(doc2)
    out: list = []
    skipped = append_component_heuristics(
        doc=doc2,
        heuristics=out,
        existing=existing,
        assets_by_id={a.id: a for a in doc2.assets},
        pack=None,
    )
    dup = [h for h in out if h.target_component_id == comp0.id and h.stride == stride0 and h.skipped_as_duplicate]
    assert dup
    assert skipped >= 1
