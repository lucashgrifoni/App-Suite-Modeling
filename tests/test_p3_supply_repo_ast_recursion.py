"""`otm import repo` reads code its user does not trust. It must not die on it.

`collect_express_routes_ast_lite` wraps `esprima.parseScript` in `try/except Exception: return []`
so a malformed file degrades to the regex heuristic — the graceful path is designed, written and
tested. The recursive walk over the resulting tree then sat *outside* that guard, and it recursed
once per node with no bound, so tree depth mapped one-to-one onto Python stack depth:

    OTM_REPO_ESPRIMA=1 otm import repo <dir>   # app.js = "a" + "+a"*1000 + ";"  (2 KB)
    RecursionError: maximum recursion depth exceeded            exit 1, raw traceback

2 KB of JavaScript, in a command whose entire purpose is analysing somebody else's repository.

The fix is an explicit work stack rather than a depth cap, and the second test below is why. A cap
would have turned an uncaught crash into silently missing routes — the same defect wearing the
other face, and much harder to notice, because the importer would report fewer endpoints with no
error at all. Nothing legitimate is refused now: a file with a pathological expression *and* real
routes yields all of its routes.

Depth is bounded upstream anyway for the shapes esprima parses recursively (400 nested blocks
already fail inside `parseScript`, where the existing guard catches them); binary-operator chains
are the shape that parses to arbitrary depth and reaches the walker, which is why they are the
payload here.
"""

from __future__ import annotations

from typing import Any

import pytest
from otm_artifact_import.repo_ast_optional import _walk, collect_express_routes_ast_lite

#: Well past `sys.getrecursionlimit()`; the pre-fix walker died at a tenth of it.
_DEEP = 5000

_ROUTE_NODE: dict[str, Any] = {
    "type": "CallExpression",
    "callee": {"type": "MemberExpression", "property": {"type": "Identifier", "name": "get"}},
    "arguments": [{"type": "Literal", "value": "/buried"}],
}


@pytest.fixture
def esprima_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_REPO_ESPRIMA", "1")


def _deep_chain(terms: int) -> str:
    """A left-nested binary expression: `a+a+a+…`. Parses fine, walks deep."""
    return "a" + "+a" * terms + ";"


def _deeply_nested_tree(depth: int, leaf: dict[str, Any]) -> dict[str, Any]:
    node = leaf
    for _ in range(depth):
        node = {"type": "ExpressionStatement", "expression": node}
    return node


# --- the hostile direction --------------------------------------------------------------------


def test_a_deeply_nested_expression_degrades_instead_of_crashing(esprima_enabled: None) -> None:
    """The reported payload: ~2 KB of JavaScript that took the whole command down."""
    assert collect_express_routes_ast_lite(_deep_chain(1000)) == []


def test_the_walker_does_not_consume_the_interpreter_stack() -> None:
    """Direct proof, independent of esprima's own parser limits."""
    hits: list[tuple[str, str]] = []
    _walk(_deeply_nested_tree(_DEEP, {"type": "Literal", "value": "leaf"}), hits)
    assert hits == []


# --- the legitimate direction: what the guard must NOT drop -----------------------------------


def test_routes_around_a_pathological_expression_are_still_reported(esprima_enabled: None) -> None:
    """A depth cap would have made this file report zero routes, silently."""
    source = f"app.get('/before', h);\n{_deep_chain(2000)}\napp.post('/after', h);"
    assert collect_express_routes_ast_lite(source) == [("get", "/before"), ("post", "/after")]


def test_a_route_buried_below_the_old_stack_limit_is_still_reported() -> None:
    """Depth must not decide whether a route is seen; only its shape does."""
    hits: list[tuple[str, str]] = []
    _walk(_deeply_nested_tree(_DEEP, _ROUTE_NODE), hits)
    assert hits == [("get", "/buried")]


def test_an_ordinary_express_file_is_unchanged(esprima_enabled: None) -> None:
    """Control: the fix cannot be implemented by disabling the walker."""
    source = "const app = express();\napp.get('/health', handler);\napp.post('/orders', handler);"
    assert collect_express_routes_ast_lite(source) == [("get", "/health"), ("post", "/orders")]
