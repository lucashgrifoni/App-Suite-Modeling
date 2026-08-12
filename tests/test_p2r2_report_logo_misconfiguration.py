"""A misconfigured `OTM_PREMIUM_LOGO_PATH` must fall back cleanly and say so.

`OTM_PREMIUM_LOGO_PATH` is a documented knob (`docs/features/PREMIUM_REPORTS.md`), and the
ordinary way to get it wrong is to point it at a company logo that happens to be a JPEG, an SVG,
or a `.png` that is really something else. `report_logo_data_uri` took the first candidate that
existed and was under the size cap, base64-encoded its raw bytes and labelled them
`data:image/png`. Measured: exit 0, a 12 461-byte PDF with no logo at all (against 401 961 bytes
with one), and the only signal was a third-party line — `Cannot identify image file:` followed by
the whole base64 blob of whatever the user pointed at — that named neither the variable nor the
file.

The bytes are now checked against the PNG signature, the built-in logo is used instead, and the
warning names `OTM_PREMIUM_LOGO_PATH` and the offending path.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from otm_report_premium.branding import report_logo_data_uri

_PNG_HEADER = b"\x89PNG\r\n\x1a\n"
_ENV = "OTM_PREMIUM_LOGO_PATH"


@pytest.fixture
def builtin_logo(monkeypatch: pytest.MonkeyPatch) -> str:
    monkeypatch.delenv(_ENV, raising=False)
    uri = report_logo_data_uri()
    assert uri is not None  # precondition: the packaged asset resolves
    return uri


def test_a_valid_png_is_used(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, builtin_logo: str) -> None:
    logo = tmp_path / "brand.png"
    logo.write_bytes(_PNG_HEADER + b"pretend pixels")
    monkeypatch.setenv(_ENV, str(logo))

    assert report_logo_data_uri() != builtin_logo


def test_a_file_that_is_not_a_png_falls_back_to_the_built_in_logo(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, builtin_logo: str
) -> None:
    """This is the case that produced a logo-less PDF and the base64 dump."""
    impostor = tmp_path / "notapng.png"
    impostor.write_bytes(b"this is definitely not a png\n")
    monkeypatch.setenv(_ENV, str(impostor))

    assert report_logo_data_uri() == builtin_logo


def test_the_rejection_names_the_variable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    impostor = tmp_path / "notapng.png"
    impostor.write_bytes(b"nope")
    monkeypatch.setenv(_ENV, str(impostor))

    with caplog.at_level(logging.WARNING, logger="otm_report_premium.branding"):
        report_logo_data_uri()

    assert _ENV in caplog.text


def test_the_rejection_names_the_offending_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    impostor = tmp_path / "notapng.png"
    impostor.write_bytes(b"nope")
    monkeypatch.setenv(_ENV, str(impostor))

    with caplog.at_level(logging.WARNING, logger="otm_report_premium.branding"):
        report_logo_data_uri()

    assert "notapng.png" in caplog.text


def test_the_rejection_does_not_echo_the_file_contents(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """The old diagnostic printed the base64 of the file — for a real logo, a console-filling blob."""
    impostor = tmp_path / "notapng.png"
    impostor.write_bytes(b"secret-looking payload")
    monkeypatch.setenv(_ENV, str(impostor))

    with caplog.at_level(logging.WARNING, logger="otm_report_premium.branding"):
        report_logo_data_uri()

    assert "secret-looking payload" not in caplog.text


def test_a_missing_path_falls_back(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, builtin_logo: str) -> None:
    monkeypatch.setenv(_ENV, str(tmp_path / "does-not-exist.png"))

    assert report_logo_data_uri() == builtin_logo


def test_a_directory_falls_back(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, builtin_logo: str) -> None:
    monkeypatch.setenv(_ENV, str(tmp_path))

    assert report_logo_data_uri() == builtin_logo


def test_an_oversized_logo_falls_back(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, builtin_logo: str) -> None:
    logo = tmp_path / "huge.png"
    logo.write_bytes(_PNG_HEADER + b"x" * 4096)
    monkeypatch.setenv(_ENV, str(logo))

    assert report_logo_data_uri(max_bytes=64) is None


def test_an_oversized_logo_is_reported(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    logo = tmp_path / "huge.png"
    logo.write_bytes(_PNG_HEADER + b"x" * 4096)
    monkeypatch.setenv(_ENV, str(logo))

    with caplog.at_level(logging.WARNING, logger="otm_report_premium.branding"):
        report_logo_data_uri(max_bytes=64)

    assert "larger than the 64-byte limit" in caplog.text


def test_a_whitespace_only_value_is_silent(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """An unset-by-whitespace variable is not a misconfiguration to shout about."""
    monkeypatch.setenv(_ENV, "   ")

    with caplog.at_level(logging.WARNING, logger="otm_report_premium.branding"):
        report_logo_data_uri()

    assert caplog.records == []


def test_the_packaged_fallback_never_warns(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    """Resolving to the built-in asset is the documented default, not a problem."""
    monkeypatch.delenv(_ENV, raising=False)

    with caplog.at_level(logging.WARNING, logger="otm_report_premium.branding"):
        report_logo_data_uri()

    assert caplog.records == []
