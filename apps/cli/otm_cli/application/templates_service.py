"""Embedded template catalog."""

from __future__ import annotations

from otm_industry_packs.template_query import filter_template_infos, get_template_info, load_all_template_infos

from otm_cli.shared.errors import CliUserError


def list_template_infos(
    *,
    category: str | None = None,
    tag: str | None = None,
    complexity: str | None = None,
    q: str | None = None,
):
    infos = load_all_template_infos()
    return filter_template_infos(
        infos,
        category=category,
        tag=tag,
        complexity=complexity,
        q=q,
    )


def get_template_detail(template_id: str):
    info = get_template_info(template_id)
    if info is None:
        raise CliUserError(
            exit_code=1,
            failed="unknown template.",
            cause=template_id,
            next_step="run `otm templates list`.",
        )
    lines = [
        f"ID: {info.id}",
        f"Title: {info.title}",
        f"Description: {info.description or '—'}",
        f"Category: {info.category_label} ({info.category})",
    ]
    if info.tags:
        lines.append(f"Tags: {', '.join(info.tags)}")
    if info.complexity:
        lines.append(f"Complexity: {info.complexity}")
    if info.best_for:
        lines.append(f"Best for: {info.best_for}")
    if info.suggested_pack:
        lines.append(f"Suggested pack: {info.suggested_pack}")
    if info.suggested_methodology:
        lines.append(f"Suggested methodology: {info.suggested_methodology}")
    if info.recommendation_hints:
        lines.append(f"Signals (recommendation): {', '.join(info.recommendation_hints)}")
    return "\n".join(lines), info.id
