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


def test_truncate_short_bytes_are_decoded() -> None:
    assert _truncate(b"ola") == "ola"


def test_truncate_long_bytes_are_capped_with_suffix() -> None:
    out = _truncate(b"x" * 4000)
    assert isinstance(out, str)
    assert "bytes suppressed" in out


def test_truncate_small_list_recurses_without_suffix() -> None:
    out = _truncate(["a", "b" * 4000])
    assert isinstance(out, list)
    assert out[0] == "a"
    assert "chars suppressed" in out[1]
    assert not any("items suppressed" in str(item) for item in out)


def test_truncate_large_dict_caps_keys() -> None:
    out = _truncate({f"k{i}": i for i in range(80)})
    assert isinstance(out, dict)
    assert out["__suppressed__"] == "30 keys suppressed"
    assert len(out) == 51  # 50 preserved keys + the suppression marker


def test_truncate_deeply_nested_value_is_suppressed() -> None:
    deep = {"a": {"b": {"c": {"d": {"e": {"f": 1}}}}}}
    out = _truncate(deep)
    assert out["a"]["b"]["c"]["d"]["e"] == "…[deep value suppressed]"


def test_truncate_scalar_values_pass_through() -> None:
    assert _truncate(123) == 123
    assert _truncate(None) is None
    assert _truncate(True) is True


def test_truncated_errors_truncates_ctx_dict() -> None:
    original = [{"type": "value_error", "ctx": {"reason": "Z" * 5000}}]
    out = _truncated_errors(original)
    assert "chars suppressed" in out[0]["ctx"]["reason"]


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
