"""Custom-rules loader: the encoding failure, and the slug contract shared by all ids.

`tests/test_custom_rules.py` covers the malformed-YAML, empty, oversized and wrong-root
rejections. The one input class it never exercises is a rules file that is not UTF-8 — a
Windows editor saving as cp1252 with an accented word in a `title:` is enough — and that path
raises `UnicodeDecodeError` from `read_text`, not `yaml.YAMLError`. If it escaped uncaught the
CLI would show a traceback instead of the actionable message every other bad file gets.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_threat_engine.custom_rules import load_custom_rules
from otm_threat_engine.custom_rules.models import is_valid_id


def test_a_rules_file_that_is_not_utf8_reports_the_encoding_not_a_traceback(tmp_path: Path) -> None:
    """`título` saved as cp1252 — the realistic way this happens."""
    latin1 = tmp_path / "rules.yaml"
    latin1.write_bytes("id: acme\nrules:\n  - title: título\n".encode("cp1252"))

    with pytest.raises(ValueError, match="not valid UTF-8"):
        load_custom_rules(latin1)


def test_the_raw_decode_error_is_wrapped_not_propagated(tmp_path: Path) -> None:
    """`UnicodeDecodeError` is itself a `ValueError`, so catching it is not enough.

    Letting it through would reach the user as a codec message about byte offsets instead of
    "rules file is not valid UTF-8".
    """
    latin1 = tmp_path / "rules.yaml"
    latin1.write_bytes(b"id: acme\nrules:\n  - title: caf\xe9\n")

    with pytest.raises(ValueError, match="rules file") as exc:
        load_custom_rules(latin1)

    assert not isinstance(exc.value, UnicodeDecodeError)


@pytest.mark.parametrize("value", ["acme", "a", "acme-prod_2", "0", "a" * 49])
def test_is_valid_id_accepts_the_slugs_the_schema_accepts(value: str) -> None:
    assert is_valid_id(value) is True


@pytest.mark.parametrize(
    "value",
    [
        "",  # empty
        "-leading-dash",  # must start alphanumeric
        "_leading_underscore",
        "Uppercase",  # ids end up in generated threat ids and filenames
        "with space",
        "acento-ç",  # non-ASCII
        "a" * 50,  # one over the 49-character cap
    ],
)
def test_is_valid_id_rejects_what_the_schema_rejects(value: str) -> None:
    assert is_valid_id(value) is False
