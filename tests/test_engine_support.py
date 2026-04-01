from pathlib import Path

from otm_core_schema import RiskAssessment, Threat, TreatmentStatus, load_document_from_yaml_path
from otm_core_schema.enums import IndustrySector, StrideCategory
from otm_industry_packs.models import AdditionalThreatRule, PackDefinition
from otm_threat_engine.engine_support import (
    build_analysis_summary,
    cross_boundary_flow_ids,
    existing_threat_keys,
    extend_with_pack_heuristics,
    recompute_summary_with_methodology,
)
from otm_threat_engine.result import AnalysisResult, AnalysisSummary, HeuristicThreat

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_existing_threat_keys_matches_document_threats_count() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    keys = existing_threat_keys(doc)
    assert len(keys) == len(doc.threats)


def test_existing_threat_keys_collapses_duplicate_stride_targets() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    base_threat = Threat(
        id="t1",
        title="one",
        stride=StrideCategory.SPOOFING,
        target_component_id="user",
        target_data_flow_id="http_in",
        treatment_status=TreatmentStatus.NEW,
    )
    doc2 = doc.model_copy(
        update={
            "threats": [
                base_threat,
                Threat(
                    id="t2",
                    title="two",
                    stride=StrideCategory.SPOOFING,
                    target_component_id="user",
                    target_data_flow_id="http_in",
                    treatment_status=TreatmentStatus.NEW,
                ),
            ]
        }
    )
    keys = existing_threat_keys(doc2)
    assert len(keys) == 1
    assert len(doc2.threats) == 2


def test_cross_boundary_flow_ids_detects_known_flow() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    ids = cross_boundary_flow_ids(doc)
    assert "http_in" in ids


def test_build_analysis_summary_counts_base_and_pack_generated() -> None:
    heuristics = [
        HeuristicThreat(
            id="h_base_active",
            title="base",
            description="base",
            stride=StrideCategory.SPOOFING,
            risk=RiskAssessment(likelihood=2, impact=3, score=6.0),
            skipped_as_duplicate=False,
        ),
        HeuristicThreat(
            id="h_base_dup",
            title="dup",
            description="dup",
            stride=StrideCategory.TAMPERING,
            risk=RiskAssessment(likelihood=2, impact=2, score=4.0),
            skipped_as_duplicate=True,
        ),
        HeuristicThreat(
            id="h_pack_active",
            title="pack",
            description="pack",
            stride=StrideCategory.REPUDIATION,
            risk=RiskAssessment(likelihood=3, impact=4, score=12.0),
            skipped_as_duplicate=False,
        ),
    ]
    summary = build_analysis_summary(
        structural_count=1,
        trust_count=1,
        heuristics=heuristics,
        base_skipped=1,
        pack_gen=1,
        pack_skip=0,
    )
    assert summary.heuristic_threats_generated == 1
    assert summary.pack_threats_generated == 1
    assert summary.heuristic_threats_skipped_duplicate == 1
    assert summary.max_risk_score is not None
    assert abs(summary.max_risk_score - 12.0) < 1e-9


def test_recompute_summary_with_methodology_counts_active_only_and_max_risk() -> None:
    result = AnalysisResult(
        engine_version="x",
        document_title="t",
        heuristic_threats=[
            HeuristicThreat(
                id="a",
                title="a",
                description="a",
                stride=StrideCategory.SPOOFING,
                risk=RiskAssessment(likelihood=2, impact=3, score=6.0),
                skipped_as_duplicate=False,
            ),
            HeuristicThreat(
                id="b",
                title="b",
                description="b",
                stride=StrideCategory.TAMPERING,
                risk=RiskAssessment(likelihood=5, impact=5, score=99.0),
                skipped_as_duplicate=True,
            ),
        ],
        summary=AnalysisSummary(),
    )
    out = recompute_summary_with_methodology(result)
    assert out.summary.heuristic_threats_generated == 1
    assert out.summary.heuristic_threats_skipped_duplicate == 1
    assert out.summary.max_risk_score is not None
    assert abs(out.summary.max_risk_score - 6.0) < 1e-9


def test_extend_with_pack_heuristics_none_returns_zeros() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    heuristics: list[HeuristicThreat] = []
    covered: set[tuple[str | None, str | None, str]] = set()
    gen, skip, hints = extend_with_pack_heuristics(
        doc=doc, heuristics=heuristics, covered=covered, pack=None
    )
    assert gen == 0
    assert skip == 0
    assert hints == []
    assert heuristics == []


def test_extend_with_pack_heuristics_appends_and_returns_hints() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    pack = PackDefinition(
        id="tp",
        name="Test Pack",
        sector=IndustrySector.GENERIC,
        control_hints=["hint-a"],
        additional_threats=[
            AdditionalThreatRule(
                id="r1",
                title="Extra",
                stride=StrideCategory.INFORMATION_DISCLOSURE,
            )
        ],
    )
    heuristics: list[HeuristicThreat] = []
    covered: set[tuple[str | None, str | None, str]] = set()
    gen, _, hints = extend_with_pack_heuristics(
        doc=doc, heuristics=heuristics, covered=covered, pack=pack
    )
    assert hints == ["hint-a"]
    assert gen >= 1
    assert len(heuristics) >= 1
    assert any(h.id.startswith("pack_tp_") for h in heuristics)
