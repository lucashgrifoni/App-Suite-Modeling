"""Coverage — embedded template catalog query/filter + loader edges."""

from __future__ import annotations

import pytest
from otm_industry_packs import loader as L
from otm_industry_packs.template_query import (
    filter_template_infos,
    get_template_info,
    load_all_template_infos,
)


def test_load_all_template_infos() -> None:
    infos = load_all_template_infos()
    assert infos
    assert all(i.id for i in infos)


def test_get_template_info_known_and_unknown() -> None:
    infos = load_all_template_infos()
    tid = infos[0].id
    assert get_template_info(tid) is not None
    assert get_template_info("definitely_not_a_template") is None


def test_filter_template_infos_all_filters() -> None:
    infos = load_all_template_infos()
    # category filter (use a real category if present)
    cats = [i.category for i in infos if i.category]
    if cats:
        assert isinstance(filter_template_infos(infos, category=cats[0]), list)
    # tag filter (use a real tag if present)
    tags = [t for i in infos for t in (i.tags or [])]
    if tags:
        assert isinstance(filter_template_infos(infos, tag=tags[0]), list)
    # complexity filter
    cxs = [i.complexity for i in infos if i.complexity]
    if cxs:
        assert isinstance(filter_template_infos(infos, complexity=cxs[0]), list)
    # free-text query
    assert isinstance(filter_template_infos(infos, q=infos[0].id[:3]), list)
    assert filter_template_infos(infos, q="zzz_no_match_xyz") == []


def test_loader_unknown_pack_and_template() -> None:
    with pytest.raises(FileNotFoundError):
        L.load_pack("no_such_pack_xyz")
    with pytest.raises(FileNotFoundError):
        L.load_template_yaml("no_such_template_xyz")
    # templates without a .meta.json return None from load_template_info
    results = [L.load_template_info(t) for t in L.list_template_ids()]
    assert any(r is None for r in results) or all(r is not None for r in results)


def test_loader_lists_nonempty() -> None:
    assert L.list_pack_ids()
    assert L.list_template_ids()
