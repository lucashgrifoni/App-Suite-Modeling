"""The importer's last-resort `RecursionError` guard still has to work.

`load_object_from_text` reads artifacts the user does not control — an OpenAPI spec, a Kubernetes
manifest, whatever a repository under evaluation happens to contain — and its contract with every
caller is that bad input is a `ValueError` (mapped to 400 / a one-line CLI error), never a
`RecursionError` escaping as a 500 with the stack on disk.

Two layers implement that. The depth ceilings in `otm_core_schema.io` refuse a nesting bomb before
the parser is ever asked to descend it, and they now do so for every payload that used to reach the
stack — which is exactly why the `except RecursionError` clause underneath them stopped being
exercised by any real input. An unexercised guard is a guard nobody would notice losing, so it is
driven directly here: force the parser to raise, and assert the translation still happens.

This is the outer layer of the same class of defect as the AST walker in
`tests/test_p3_supply_repo_ast_recursion.py` — untrusted input, unbounded recursion, a guard that
was one line away from where the exception actually came out.
"""

from __future__ import annotations

import pytest
from otm_artifact_import import _yamljson


def _raise_recursion_error(_text: str) -> dict[str, object]:
    raise RecursionError("maximum recursion depth exceeded")


def test_a_recursion_error_from_the_json_parser_becomes_an_actionable_value_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Defence in depth below the ceilings: still `ValueError`, still 400, never a 500."""
    monkeypatch.setattr(_yamljson, "json_loads_bounded", _raise_recursion_error)

    with pytest.raises(ValueError, match="aninhado"):
        _yamljson.load_object_from_text('{"a": 1}')


def test_the_guard_preserves_the_original_exception_as_the_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`from e` is what keeps the real origin in the log while the caller sees a user error."""
    monkeypatch.setattr(_yamljson, "json_loads_bounded", _raise_recursion_error)

    with pytest.raises(ValueError) as raised:
        _yamljson.load_object_from_text('{"a": 1}')

    assert isinstance(raised.value.__cause__, RecursionError)


def test_ordinary_json_is_unaffected_by_the_guard() -> None:
    """Control: the guard must not be reachable for input that parses perfectly well."""
    assert _yamljson.load_object_from_text('{"a": 1}') == {"a": 1}
