"""Checks simples para coerência da documentação multi-engine."""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _read(rel: str) -> str:
    return (_ROOT / rel).read_text(encoding="utf-8").lower()


def test_readme_mentions_stride_as_default_and_incremental_engines() -> None:
    text = _read("README.md")
    assert "stride" in text
    assert "default" in text
    assert "linddun" in text
    assert "pasta" in text
    assert "plot4ai" in text
    assert "incremental" in text or "incrementalmente" in text


def test_multi_engine_doc_has_comparison_matrix() -> None:
    text = _read("docs/features/MULTI_ENGINE_ARCHITECTURE.md")
    assert (
        "| metodologia | objetivo | quando usar | complexidade | maturidade | "
        "recomendação automática | perfil ideal |" in text
    )
    assert "linddun" in text
    assert "nist data-centric" in text
    assert "octave allegro" in text
    assert "cia / cia-die" in text
    assert "pasta" in text
    assert "plot4ai" in text


def test_docs_include_cli_api_ui_examples_and_when_to_use_table() -> None:
    readme = _read("README.md")
    assert "methodology matrix" in readme or "multi-methodology" in readme
    assert "cli" in readme
    assert "api" in readme
    assert "web ui" in readme or "interface web" in readme

    cli = _read("docs/features/CLI.md")
    assert "## exemplos por metodologia" in cli
    assert "--methodology stride" in cli
    assert "--methodology linddun" in cli
    assert "--methodology nist_data_centric" in cli
    assert "--methodology plot4ai" in cli

    api = _read("docs/features/API.md")
    assert "## exemplos por metodologia (`post /v1/models/analyze`)" in api
    assert '"methodology": "stride"' in api
    assert '"methodology": "linddun"' in api
    assert '"methodology": "pasta"' in api
    assert '"methodology": "plot4ai"' in api

    ui = _read("docs/features/UI.md")
    assert "hint curto por metodologia" in ui
    assert "exemplos por metodologia (fluxo ui)" in ui


def test_branding_docs_exist_and_use_app_suite_modeling() -> None:
    readme = _read("README.md")
    branding = _read("docs/features/BRANDING.md")
    docs_index = _read("docs/README.md")
    assert "app suite modeling" in readme
    assert "branding" in readme
    assert "paleta oficial" in branding
    assert "tokens de design" in branding
    assert "sistema de logo" in branding
    assert "branding.md" in docs_index or "features/branding.md" in docs_index
