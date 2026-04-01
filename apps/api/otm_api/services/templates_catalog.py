"""Listagem de templates embutidos (metadados para a UI e filtros server-side)."""

from __future__ import annotations

from otm_industry_packs.models import TemplateInfo
from otm_industry_packs.template_query import (
    filter_template_infos,
    get_template_info,
    load_all_template_infos,
)
from pydantic import BaseModel, Field


class TemplateListItem(BaseModel):
    id: str
    title: str
    description: str = ""
    suggested_pack: str | None = None
    category: str = "applications"
    category_label: str = "Aplicações"
    tags: list[str] = Field(default_factory=list)
    complexity: str | None = None
    best_for: str | None = None
    suggested_methodology: str | None = None
    recommendation_hints: list[str] = Field(default_factory=list)


def _to_item(info: TemplateInfo) -> TemplateListItem:
    return TemplateListItem(
        id=info.id,
        title=info.title,
        description=info.description,
        suggested_pack=info.suggested_pack,
        category=info.category,
        category_label=info.category_label,
        tags=list(info.tags),
        complexity=info.complexity,
        best_for=info.best_for,
        suggested_methodology=info.suggested_methodology,
        recommendation_hints=list(info.recommendation_hints),
    )


def list_templates() -> list[TemplateListItem]:
    return [_to_item(i) for i in load_all_template_infos()]


def get_template(template_id: str) -> TemplateListItem | None:
    info = get_template_info(template_id)
    if info is None:
        return None
    return _to_item(info)


def list_templates_filtered(
    *,
    category: str | None = None,
    tag: str | None = None,
    complexity: str | None = None,
    q: str | None = None,
) -> list[TemplateListItem]:
    infos = load_all_template_infos()
    infos = filter_template_infos(
        infos,
        category=category,
        tag=tag,
        complexity=complexity,
        q=q,
    )
    return [_to_item(i) for i in infos]
