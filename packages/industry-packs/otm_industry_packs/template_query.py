"""Consulta e filtro do catálogo embutido (uso API, CLI e testes)."""

from __future__ import annotations

from otm_industry_packs.loader import list_template_ids, load_template_info
from otm_industry_packs.models import TemplateInfo


def load_all_template_infos() -> list[TemplateInfo]:
    """Uma entrada por ficheiro `*.otm.yaml`, com manifest opcional."""
    out: list[TemplateInfo] = []
    for tid in list_template_ids():
        info = load_template_info(tid)
        if info:
            out.append(info)
        else:
            out.append(TemplateInfo(id=tid, title=tid, description=""))  # pragma: no cover - defensive: shipped templates always have a manifest
    return out


def get_template_info(template_id: str) -> TemplateInfo | None:
    if template_id not in set(list_template_ids()):
        return None
    info = load_template_info(template_id)
    if info:
        return info
    return TemplateInfo(id=template_id, title=template_id, description="")  # pragma: no cover - defensive: shipped templates always have a manifest


def filter_template_infos(
    items: list[TemplateInfo],
    *,
    category: str | None = None,
    tag: str | None = None,
    complexity: str | None = None,
    q: str | None = None,
) -> list[TemplateInfo]:
    out = items
    if category:
        c = category.strip().lower()
        out = [x for x in out if x.category.lower() == c]
    if tag:
        t = tag.strip().lower()
        out = [x for x in out if any(h.lower() == t for h in x.tags)]
    if complexity:
        cx = complexity.strip().lower()
        out = [x for x in out if (x.complexity or "").lower() == cx]
    if q and q.strip():
        needle = q.strip().lower()
        out = [
            x
            for x in out
            if needle in x.id.lower()
            or needle in x.title.lower()
            or needle in (x.description or "").lower()
            or any(needle in h.lower() for h in x.tags)
            or (x.best_for and needle in x.best_for.lower())
        ]
    return out
