"""Fallback paths of the optional `esprima` JS parser (`repo_ast_optional`).

The whole point of this module is that it is *optional*: the repo importer must degrade to
"no routes found" instead of failing when the parser is missing or the source is unparseable.
Those degradation paths are the ones a user actually hits (a repo with a broken file, an
install without the extra), and none of them were exercised.
"""

from __future__ import annotations

import sys

import pytest
from otm_artifact_import.repo_ast_optional import collect_express_routes_ast_lite


@pytest.fixture
def esprima_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_REPO_ESPRIMA", "1")


def test_a_literal_route_is_reported(esprima_enabled: None) -> None:
    """Control for the fallback tests below: the happy path really does return something."""
    assert collect_express_routes_ast_lite("app.get('/health', handler);") == [("get", "/health")]


def test_a_route_registered_from_a_variable_is_not_reported(esprima_enabled: None) -> None:
    """`app.get(routePath, handler)` has no literal to record.

    The importer only claims routes it can name. Reporting the identifier `routePath` as if it
    were the URL would put a fabricated endpoint into the threat model.
    """
    assert collect_express_routes_ast_lite("const routePath = '/x';\napp.get(routePath, handler);") == []


def test_missing_esprima_degrades_to_no_routes(
    esprima_enabled: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`esprima` is an optional extra; without it the importer must still succeed."""
    monkeypatch.setitem(sys.modules, "esprima", None)
    assert collect_express_routes_ast_lite("app.get('/health', handler);") == []


def test_unparseable_source_degrades_to_no_routes(esprima_enabled: None) -> None:
    """One broken file in a scanned repo must not abort the whole import."""
    assert collect_express_routes_ast_lite("app.get('/health', handler);\nfunction (") == []


def test_the_flag_is_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OTM_REPO_ESPRIMA", raising=False)
    assert collect_express_routes_ast_lite("app.get('/health', handler);") == []
