from __future__ import annotations

from fastapi import APIRouter, Path, status
from pydantic import ValidationError as PydanticValidationError

from otm_api.routers._errors import raise_template_invalid, raise_template_not_found
from otm_api.schemas.bodies import CreateModelResponse
from otm_api.services.documents import document_from_template
from otm_api.services.templates_catalog import TemplateListItem, list_templates

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get(
    "",
    response_model=list[TemplateListItem],
    summary="Listar templates",
    description="Templates embutidos no pacote `otm_industry_packs` (IDs usados em `otm init -t`).",
)
def get_templates() -> list[TemplateListItem]:
    return list_templates()


@router.post(
    "/{template_id}/instantiate",
    response_model=CreateModelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Gerar modelo a partir de template",
    description="Carrega o YAML do template e devolve o documento canónico validado.",
)
def instantiate_template(
    template_id: str = Path(..., description="ID do template (ex.: saas-web)."),
) -> CreateModelResponse:
    try:
        doc = document_from_template(template_id)
    except FileNotFoundError as e:
        raise raise_template_not_found(e) from e
    except PydanticValidationError as e:
        raise raise_template_invalid(e) from e
    return CreateModelResponse(document=doc.model_dump(mode="json", by_alias=True))
