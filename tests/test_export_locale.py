"""Política de locale para artefactos de exportação."""

from __future__ import annotations

from otm_exporters.export_locale import normalize_export_locale


def test_normalize_export_locale_omitted_defaults_pt_br() -> None:
    assert normalize_export_locale(None) == "pt-BR"
    assert normalize_export_locale("") == "pt-BR"
    assert normalize_export_locale("   ") == "pt-BR"


def test_normalize_export_locale_allowed() -> None:
    assert normalize_export_locale("pt-BR") == "pt-BR"
    assert normalize_export_locale("en") == "en"
    assert normalize_export_locale("  en  ") == "en"


def test_normalize_export_locale_bcp47_variants() -> None:
    assert normalize_export_locale("PT-BR") == "pt-BR"
    assert normalize_export_locale("pt_br") == "pt-BR"
    assert normalize_export_locale("pt") == "pt-BR"
    assert normalize_export_locale("pt-PT") == "pt-BR"
    assert normalize_export_locale("en-US") == "en"
    assert normalize_export_locale("EN") == "en"


def test_normalize_export_locale_invalid_falls_back_en() -> None:
    assert normalize_export_locale("fr") == "en"
    assert normalize_export_locale("../../../etc/passwd") == "en"
    assert normalize_export_locale("<script>") == "en"
    assert normalize_export_locale("de-DE") == "en"
