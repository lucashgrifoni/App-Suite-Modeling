from __future__ import annotations

from fastapi import APIRouter, Path, Query, status
from pydantic import ValidationError as PydanticValidationError

from otm_api.routers._errors import raise_template_invalid, raise_template_not_found
from otm_api.schemas.bodies import CreateModelResponse
from otm_api.services.documents import document_from_template
from otm_api.services.templates_catalog import (
    TemplateListItem,
    get_template,
    list_templates,
    list_templates_filtered,
)

router = APIRouter(prefix="/templates", tags=["Templates"])


@router.get(
    "",
    summary="List templates",
    description=(
        "Built-in templates from `otm_industry_packs` (IDs used with `otm init -t`). "
        "Optional query filters combine with AND semantics."
    ),
)
def get_templates(
    category: str | None = Query(
        default=None,
        description="Filtra pela chave `category` (ex.: applications, ai_llm).",
    ),
    tag: str | None = Query(default=None, description="Corresponde a uma tag (exata, case-insensitive)."),
    complexity: str | None = Query(
        default=None,
        description="low | medium | high",
    ),
    q: str | None = Query(
        default=None,
        description="Texto livre em id, título, descrição, tags ou best_for.",
    ),
) -> list[TemplateListItem]:
    if category or tag or complexity or q:
        return list_templates_filtered(
            category=category,
            tag=tag,
            complexity=complexity,
            q=q,
        )
    return list_templates()


@router.get(
    "/{template_id}",
    summary="Get template metadata",
    description="Detalhe de um template embutido (metadados do manifest).",
)
def get_template_detail(
    template_id: str = Path(..., description="Template ID (ex.: api-public)."),
) -> TemplateListItem:
    item = get_template(template_id)
    if item is None:
        raise raise_template_not_found(template_id)
    return item


# HEAD acompanha GET (RFC 9110 9.3.2): verificadores de links, caches e sondas usam-no, e
# `/openapi.json` e `/docs` — servidos pelo `Route` do Starlette — já respondiam, enquanto
# estas rotas davam 405. Mesmo padrão de `/health` em system.py: rota separada e fora do
# schema, porque uma única rota com GET+HEAD reutilizaria o `operationId` nos dois métodos e
# produziria um OpenAPI inválido. Reaproveita a função do GET, para não duplicar parâmetros.
router.add_api_route("", get_templates, methods=["HEAD"], include_in_schema=False)
router.add_api_route("/{template_id}", get_template_detail, methods=["HEAD"], include_in_schema=False)


@router.post(
    "/{template_id}/instantiate",
    status_code=status.HTTP_201_CREATED,
    summary="Instantiate model from template",
    description="Loads template YAML and returns the validated canonical document.",
)
def instantiate_template(
    template_id: str = Path(..., description="Template ID (e.g. saas-web)."),
) -> CreateModelResponse:
    try:
        doc = document_from_template(template_id)
    except FileNotFoundError as e:
        raise raise_template_not_found(template_id) from e
    except PydanticValidationError as e:  # pragma: no cover - defensive guard
        raise raise_template_invalid(e) from e
    return CreateModelResponse(document=doc.model_dump(mode="json", by_alias=True))
