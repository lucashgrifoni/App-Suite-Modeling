"""Listagem de templates embutidos (metadados para a UI)."""

from __future__ import annotations

from otm_industry_packs.loader import list_template_ids, load_template_info
from pydantic import BaseModel


class TemplateListItem(BaseModel):
    id: str
    title: str
    description: str = ""
    suggested_pack: str | None = None


def list_templates() -> list[TemplateListItem]:
    out: list[TemplateListItem] = []
    for tid in list_template_ids():
        info = load_template_info(tid)
        if info:
            out.append(
                TemplateListItem(
                    id=info.id,
                    title=info.title,
                    description=info.description,
                    suggested_pack=info.suggested_pack,
                )
            )
        else:
            out.append(TemplateListItem(id=tid, title=tid, description=""))
    return out
