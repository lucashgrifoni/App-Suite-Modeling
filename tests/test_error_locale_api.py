"""Resolução de locale para mensagens de erro da API."""

from __future__ import annotations

import pytest
from otm_api.error_locale import resolve_api_error_locale_from_accept_language


@pytest.mark.parametrize(
    ("header", "expected"),
    [
        (None, "en"),
        ("", "en"),
        ("en", "en"),
        ("en-US", "en"),
        ("en-GB;q=0.9, pt-BR;q=0.8", "en"),
        ("pt-BR", "pt-BR"),
        ("pt-PT,en;q=0.8", "pt-BR"),
        ("pt", "pt-BR"),
        ("fr-FR, en;q=0.9", "en"),
        ("de-DE", "en"),
    ],
)
def test_resolve_api_error_locale_from_accept_language(header: str | None, expected: str) -> None:
    assert resolve_api_error_locale_from_accept_language(header) == expected
