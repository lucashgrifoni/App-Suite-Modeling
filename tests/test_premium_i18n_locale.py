"""Normalização de locale do report premium."""

from otm_report_premium.i18n_locale import normalize_premium_locale


def test_normalize_premium_locale_omitted_is_pt_br() -> None:
    assert normalize_premium_locale(None) == "pt-BR"
    assert normalize_premium_locale("") == "pt-BR"


def test_normalize_premium_locale_allowlist() -> None:
    assert normalize_premium_locale("pt-BR") == "pt-BR"
    assert normalize_premium_locale("en") == "en"


def test_normalize_premium_locale_invalid_falls_back_en() -> None:
    assert normalize_premium_locale("fr") == "en"
    assert normalize_premium_locale("../../../etc/passwd") == "en"


def test_normalize_premium_locale_matches_export_module() -> None:
    assert normalize_premium_locale("en-GB") == "en"
    assert normalize_premium_locale("pt_br") == "pt-BR"
