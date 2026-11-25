"""Actionable remediation backlog from model + analysis."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import PlainTextResponse
from otm_threat_engine import AnalysisResult
from otm_threat_engine.remediation import RemediationBacklog
from pydantic import ValidationError as PydanticValidationError

from otm_api.api_error_messages import msg_remediation_group_by_invalid
from otm_api.error_models import API_ERROR_RESPONSES
from otm_api.routers._errors import (
    document_from_payload_or_422,
    ensure_analysis_matches_document,
    error_detail,
    raise_analysis_validation_error,
    raise_pack_not_found,
)
from otm_api.schemas.bodies import RemediationBacklogRequest
from otm_api.services.remediation import build_remediation_backlog_response

router = APIRouter(prefix="/remediation", tags=["Remediation"], responses=API_ERROR_RESPONSES)

# Os mesmos três valores que `docs/features/REMEDIATION_BACKLOG.md`, a descrição do parâmetro e
# o `--group-by` da CLI aceitam.
_GROUP_BY_VALUES = ("root-cause", "control", "category")


def _validated_group_by(value: str | None) -> str | None:
    """
    422 em vez de cair no agrupamento por defeito.

    `export_remediation_backlog_markdown` ignora o que não reconhece, por isso `root_cause`
    (underscore), `severity` ou `totally-bogus` devolviam 200 com um relatório byte-a-byte
    igual ao default: o utilizador recebia um agrupamento que não pediu e nada lho dizia. O
    parâmetro vizinho `format` já é estrito, e o `--group-by` da CLI também.
    """
    if value is None or value in _GROUP_BY_VALUES:
        return value
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=error_detail(
            code="REMEDIATION_GROUP_BY_INVALID",
            message=msg_remediation_group_by_invalid(value=value, accepted=", ".join(_GROUP_BY_VALUES)),
        ),
    )


@router.post(
    "/backlog",
    summary="Generate remediation backlog",
    description=(
        "Body: canonical `document`; optional `analysis` (`AnalysisResult`). "
        "If `analysis` is omitted, set `run_analysis: true` to run the engine."
    ),
    response_model=RemediationBacklog,
    responses={
        200: {
            "description": "JSON (`format=json`, default) ou Markdown (`format=markdown`).",
            "content": {
                "text/markdown": {
                    "schema": {"type": "string"},
                    "example": "## Remediação\n\nItens priorizados…",
                },
            },
        },
    },
)
def post_remediation_backlog(
    body: RemediationBacklogRequest,
    export_format: Annotated[
        Literal["json", "markdown"],
        Query(
            alias="format",
            description="json = full object; markdown = human-readable report.",
        ),
    ] = "json",
    group_by: Annotated[
        str | None,
        Query(description="For Markdown: root-cause | control | category."),
    ] = None,
) -> RemediationBacklog | PlainTextResponse:
    grouping = _validated_group_by(group_by)
    doc = document_from_payload_or_422(body.document)
    analysis_obj: AnalysisResult | None = None
    if body.analysis is not None:
        try:
            analysis_obj = AnalysisResult.model_validate(body.analysis)
        except PydanticValidationError as e:
            raise raise_analysis_validation_error(e) from e
        ensure_analysis_matches_document(doc, analysis_obj)

    # Com `run_analysis`, esta rota corre o motor e o loader de packs pode levantar
    # `FileNotFoundError`. Sem este mapeamento, um `pack_id` errado saía como 500
    # genérico aqui, enquanto as outras rotas do motor devolvem 404 PACK_NOT_FOUND
    # (ver exports.py / models.py / reports_premium.py).
    try:
        backlog = build_remediation_backlog_response(
            doc,
            analysis_obj,
            run_analysis=body.run_analysis,
            pack_id=body.pack_id,
            methodology=body.methodology,
            auto_recommend_methodology=body.auto_recommend_methodology,
        )
    except FileNotFoundError as e:
        raise raise_pack_not_found(body.pack_id) from e
    if export_format == "markdown":
        from otm_exporters import export_remediation_backlog_markdown

        text = export_remediation_backlog_markdown(backlog, group_by=grouping)
        return PlainTextResponse(text, media_type="text/markdown; charset=utf-8")
    return backlog
