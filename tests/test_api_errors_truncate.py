"""Regression — API 422 input echo truncation (D4 from v7.5.0 validation)."""

from __future__ import annotations

from otm_api.errors import _truncate, _truncated_errors  # type: ignore[attr-defined]


def test_truncate_short_string_passes_through() -> None:
    assert _truncate("ola") == "ola"


def test_truncate_long_string_is_capped_with_suffix() -> None:
    out = _truncate("x" * 4000)
    assert isinstance(out, str)
    assert len(out) < 4000
    assert "chars suppressed" in out


def test_truncate_nested_dict_caps_string_inside() -> None:
    payload = {"metadata": {"title": "T" * 10000}}
    out = _truncate(payload)
    assert isinstance(out, dict)
    title = out["metadata"]["title"]
    assert "chars suppressed" in title


def test_truncate_long_list_is_capped() -> None:
    out = _truncate([f"item_{i}" for i in range(200)])
    assert isinstance(out, list)
    assert any("items suppressed" in str(item) for item in out)


def test_truncated_errors_keeps_other_fields() -> None:
    original = [
        {
            "type": "missing",
            "loc": ["body", "document"],
            "msg": "Field required",
            "input": {"title": "Z" * 5000},
        }
    ]
    out = _truncated_errors(original)
    assert out[0]["type"] == "missing"
    assert out[0]["loc"] == ["body", "document"]
    assert out[0]["msg"] == "Field required"
    title = out[0]["input"]["title"]
    assert "chars suppressed" in title
