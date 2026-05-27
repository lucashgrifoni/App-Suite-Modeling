"""Coverage — analysis markdown exporter across view modes and rich business models."""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_core_schema import load_document_from_yaml_path
from otm_exporters import export_analysis_markdown
from otm_threat_engine import analyze_document

_ROOT = Path(__file__).resolve().parents[1]
_RICH = [
    _ROOT / "examples" / "test-apps" / "ecommerce-subscription.otm.yaml",
    _ROOT / "examples" / "test-apps" / "finance-wallet.otm.yaml",
    _ROOT / "examples" / "saas-ordering-v1.otm.yaml",
]


@pytest.mark.parametrize("model", _RICH)
@pytest.mark.parametrize("view_mode", ["legacy", "harmonized"])
def test_analysis_markdown_view_modes(model: Path, view_mode: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_MARKDOWN_VIEW_MODE", view_mode)
    res = analyze_document(load_document_from_yaml_path(model))
    md = export_analysis_markdown(res)
    assert md and "##" in md


def test_analysis_markdown_invalid_view_mode_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTM_MARKDOWN_VIEW_MODE", "nonsense")
    res = analyze_document(load_document_from_yaml_path(_RICH[0]))
    assert export_analysis_markdown(res)


def test_analysis_markdown_locale_and_row_cap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OTM_MARKDOWN_VIEW_MODE", raising=False)
    res = analyze_document(load_document_from_yaml_path(_RICH[1]))
    assert export_analysis_markdown(res, max_heuristic_rows=1, locale="en")
    assert export_analysis_markdown(res, max_heuristic_rows=1000, locale="pt-BR")
