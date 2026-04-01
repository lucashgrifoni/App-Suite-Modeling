from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import ValidationError as PydanticValidationError

from otm_api.routers._errors import raise_analysis_validation_error
from otm_api.schemas.bodies import AnalysisDiffBody
from otm_api.services.compare import analysis_diff_from_payloads

router = APIRouter(prefix="/analyses", tags=["Análises"])


@router.post(
    "/diff",
    summary="Diff entre dois resultados de análise",
    description="Compara dois `AnalysisResult` (JSON). Útil para CI sem reexecutar o motor.",
    response_description="Objeto `AnalysisDiff` serializado.",
)
def diff_analysis_results_route(body: AnalysisDiffBody) -> dict[str, Any]:
    try:
        return analysis_diff_from_payloads(
            baseline_analysis=body.baseline_analysis,
            revised_analysis=body.revised_analysis,
        ).model_dump(mode="json")
    except PydanticValidationError as e:
        raise raise_analysis_validation_error(e) from e
