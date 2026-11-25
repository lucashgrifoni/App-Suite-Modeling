"""P4 regression — listing the built-in catalogue must not re-glob it once per template.

`load_all_template_infos` calls `list_template_ids()` to enumerate the catalogue, then calls
`load_template_info(tid)` for each id — and that helper calls `list_template_ids()` *again* to
validate the id it was just handed. With 38 shipped templates that is 39 directory globs per call.

Measured against a real uvicorn, `GET /v1/templates` was the **slowest route in the API**: p50
43.5 ms, against 20.7 ms for `POST /v1/models/analyze`, which runs the whole STRIDE engine. Serving
a static catalogue cost more than analysing a threat model. Of the 18.4 ms the loader itself spends,
6.2 ms is the 39 globs and 2.3 ms is reading and validating the 38 manifests; the rest is the
per-template `is_file()` and list rebuilding that the repeated enumeration drags along.

The catalogue is package data. It cannot change while the process lives, which is why the same
`@lru_cache(maxsize=1)` treatment already applies to the framework registries in this repo.

Two properties matter more than the speed, and both are pinned below: the returned list must stay
safe to mutate (a cache handing out its own list would let one caller corrupt every later one), and
the id membership test is the path-traversal defence for `load_pack` and `load_template_yaml` — it
has to keep rejecting exactly what it rejected before.
"""

from __future__ import annotations

from pathlib import Path

import otm_industry_packs
import pytest
from otm_industry_packs.loader import (
    list_pack_ids,
    list_template_ids,
    load_pack,
    load_template_yaml,
)
from otm_industry_packs.template_query import load_all_template_infos


@pytest.fixture
def glob_counter(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Records every directory glob, so the oracle is a count and not a stopwatch."""
    calls: list[str] = []
    original = Path.glob

    def counting(self: Path, pattern: str, **kwargs: object):  # type: ignore[no-untyped-def]
        calls.append(f"{self.name}/{pattern}")
        return original(self, pattern, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "glob", counting)
    return calls


def test_listing_the_catalogue_globs_the_directory_once(glob_counter: list[str]) -> None:
    infos = load_all_template_infos()

    assert len(infos) > 1, "the catalogue must be non-empty, or this proves nothing"
    assert len(glob_counter) <= 1, f"{len(infos)} templates cost {len(glob_counter)} globs"


def test_the_number_of_globs_does_not_grow_with_the_catalogue(glob_counter: list[str]) -> None:
    """Constant, not merely small: the count must not track the number of templates."""
    load_all_template_infos()
    first = len(glob_counter)
    load_all_template_infos()

    assert len(glob_counter) == first, "a second listing re-globbed the directory"


def test_the_returned_id_list_is_safe_to_mutate() -> None:
    """A cache that hands out its own list lets one caller corrupt every later one."""
    ids = list_template_ids()
    ids.append("not-a-template")
    ids.clear()

    assert list_template_ids(), "the catalogue was emptied by a caller mutating its result"
    assert "not-a-template" not in list_template_ids()
    packs = list_pack_ids()
    packs.clear()
    assert list_pack_ids(), "the pack list was emptied by a caller mutating its result"


def test_the_catalogue_still_matches_what_is_on_disk() -> None:
    """Behaviour lock: caching may not change which templates exist."""
    data = Path(otm_industry_packs.__file__).resolve().parent / "data" / "templates"
    on_disk = sorted(p.name.removesuffix(".otm.yaml") for p in data.glob("*.otm.yaml"))

    assert list_template_ids() == on_disk


@pytest.mark.parametrize(
    "hostile",
    ["../packs/saas", "../../etc/passwd", "/etc/passwd", "saas/../../secret", "", "."],
)
def test_the_membership_check_still_refuses_traversal(hostile: str) -> None:
    """The id list is the traversal defence for both loaders; caching must not soften it."""
    with pytest.raises(FileNotFoundError):
        load_template_yaml(hostile)
    with pytest.raises(FileNotFoundError):
        load_pack(hostile)
