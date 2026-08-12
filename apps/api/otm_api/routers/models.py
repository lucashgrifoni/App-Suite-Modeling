from __future__ import annotations

from fastapi import APIRouter, status
from otm_core_schema import diff_documents
from otm_core_schema.diff import ThreatModelDiff
from otm_core_schema.model_quality_precheck import assess_model_precheck
from otm_threat_engine import recommend_methodology
from otm_threat_engine.comparison_models import ThreatModelComparisonResult
from otm_threat_engine.methodology_completeness import assess_methodology_completeness
from otm_threat_engine.result import AnalysisResult

from otm_api.routers._errors import (
    analysis_from_payload_or_422,
    document_from_payload_or_422,
    ensure_analysis_matches_document,
    raise_pack_not_found,
)
from otm_api.schemas.bodies import (
    AnalyzeBody,
    CompareBody,
    CreateModelResponse,
    DiffBody,
    DocumentBody,
    ModelPrecheckResponse,
    PrecheckBody,
    RecommendMethodologyResponse,
    ValidateResponse,
)
from otm_api.services.analysis import run_analysis
from otm_api.services.compare import comparison_from_validated_documents
from otm_api.services.documents import create_blank_document

router = APIRouter(prefix="/models", tags=["Models"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="Create blank model",
    description=("Returns a minimal valid `ThreatModelDocument` (same as `otm init` without a template)."),
)
def create_model() -> CreateModelResponse:
    doc = create_blank_document()
    return CreateModelResponse(document=doc.model_dump(mode="json", by_alias=True))


@router.post(
    "/validate",
    summary="Validate model",
    description="Validates the payload against the canonical schema; does not persist data.",
)
def validate_model(body: DocumentBody) -> ValidateResponse:
    doc = document_from_payload_or_422(body.document)
    return ValidateResponse(
        title=doc.metadata.title,
        schema_version=doc.model_info.schema_version,
        component_count=len(doc.components),
        threat_count=len(doc.threats),
    )


@router.post(
    "/precheck",
    summary="Model quality pre-check",
    description=(
        "Avalia completude do modelo (score, banda, matriz de adequação metodológica) e, "
        "opcionalmente, estado de completude da metodologia escolhida — sem correr heurísticas STRIDE."
    ),
    response_description="`precheck` + `methodology_completeness` serializados.",
)
def model_precheck(body: PrecheckBody) -> ModelPrecheckResponse:
    doc = document_from_payload_or_422(body.document)
    chosen = body.methodology or doc.model_info.methodology
    return ModelPrecheckResponse(
        precheck=assess_model_precheck(doc),
        methodology_completeness=assess_methodology_completeness(doc, chosen),
    )


@router.post(
    "/diff",
    summary="Diff model versions",
    description=(
        "Compares two canonical versions (baseline vs revised) and returns structured diff. "
        "Implemented in `otm_core_schema.diff_documents` — same semantics as `otm diff` in the CLI."
    ),
    response_description="Serialized `ThreatModelDiff` JSON object.",
)
def diff_model_versions(body: DiffBody) -> ThreatModelDiff:
    baseline = document_from_payload_or_422(body.baseline)
    revised = document_from_payload_or_422(body.revised)
    return diff_documents(baseline, revised)


@router.post(
    "/compare",
    summary="Compare models (structure and optional analysis)",
    description=(
        "Returns `ThreatModelComparisonResult`: canonical diff, aggregates, insights and, when "
        "`baseline_analysis`/`revised_analysis` or `run_analysis=true` is provided, risk/heuristic delta."
    ),
    response_description="JSON of the unified comparison result.",
)
def compare_models(body: CompareBody) -> ThreatModelComparisonResult:
    b_doc = document_from_payload_or_422(body.baseline)
    r_doc = document_from_payload_or_422(body.revised)
    b_analysis = analysis_from_payload_or_422(body.baseline_analysis)
    r_analysis = analysis_from_payload_or_422(body.revised_analysis)
    # Cada análise tem de descrever o documento que vem ao lado dela. Sem isto, trocar as duas
    # (um copy/paste num passo de CI) devolvia 200 com o delta ao contrário: as ameaças que a
    # revisão *removeu* apareciam como "added", com a metade estrutural do resultado — essa
    # calculada a partir dos documentos certos — a dar-lhe ar de resposta legítima.
    if b_analysis is not None and r_analysis is not None:
        ensure_analysis_matches_document(
            b_doc, b_analysis, analysis_field="baseline_analysis", document_field="baseline"
        )
        ensure_analysis_matches_document(r_doc, r_analysis, analysis_field="revised_analysis", document_field="revised")
    try:
        result = comparison_from_validated_documents(
            b_doc,
            r_doc,
            baseline_analysis=b_analysis,
            revised_analysis=r_analysis,
            run_analysis_flag=body.run_analysis,
            pack_id=body.pack_id,
        )
    except FileNotFoundError as e:
        raise raise_pack_not_found(e) from e
    return result


@router.post(
    "/recommend-methodology",
    summary="Recommend methodology / engine",
    description="Suggests a methodology based on document context.",
)
def recommend_methodology_for_model(body: DocumentBody) -> RecommendMethodologyResponse:
    doc = document_from_payload_or_422(body.document)
    rec = recommend_methodology(doc)
    return RecommendMethodologyResponse(
        methodology=rec.methodology,
        reason=rec.reason,
        explanations=list(rec.explanations),
        methodology_scores=rec.methodology_scores,
        runner_up_methodology=rec.runner_up_methodology,
        runner_up_score=rec.runner_up_score,
        score_gap=rec.score_gap,
        recommendation_confidence=rec.recommendation_confidence,
        top_supporting_signals=list(rec.top_supporting_signals),
        counter_signals=list(rec.counter_signals),
    )


@router.post(
    "/analyze",
    summary="Analyze model",
    description="Runs the STRIDE engine, trust boundaries, and risk; optional industry pack.",
    response_description="Serialized `AnalysisResult` JSON.",
)
def analyze_model(body: AnalyzeBody) -> AnalysisResult:
    doc = document_from_payload_or_422(body.document)
    try:
        result = run_analysis(
            doc,
            pack_id=body.pack_id,
            methodology=body.methodology,
            auto_recommend_methodology=body.auto_recommend_methodology,
        )
    except FileNotFoundError as e:
        raise raise_pack_not_found(e) from e
    return result
