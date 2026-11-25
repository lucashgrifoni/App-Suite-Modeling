"""`export_analysis_markdown(locale="en")` must not leave one section in Portuguese.

Reported from the web Export screen with "Language for Markdown / PDF exports" = English: the
whole risk-consolidation block came out Portuguese — heading and every bullet label — sandwiched
between the English "### Framework references (aggregate)" and "### Structural warnings", which
proves the locale was honoured everywhere else. Cause: `_append_aggregate_risk_and_cockpit`,
`_append_aggregate_block`, `_append_top_groups` and `_append_cockpit_block` were the only
builders in the file that never took the `AnalysisMarkdownMessages` bundle.

The same block also interpolated a `dict` straight into the report, so the delivered Markdown
carried a Python repr — ``{'high': 13, 'medium': 3}``, single quotes and all.

Scope note: threat titles, `mitigation_starters` and the cockpit `headline` are produced by the
engine and are Portuguese in the `en` export exactly as every other engine-generated string is
(`[spoofing] Serviço de API` appears in both locales). That is a separate, product-wide decision
about engine content; what the exporter owns is the section chrome, and that is what these tests
pin.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_core_schema import load_document_from_yaml_path
from otm_exporters import export_analysis_markdown
from otm_threat_engine import analyze_document
from otm_threat_engine.result import AnalysisResult

_MODEL = Path(__file__).resolve().parents[1] / "examples" / "saas-ordering-v1.otm.yaml"

_PORTUGUESE_LABELS = [
    "Consolidação de risco e cockpit executivo",
    "Ameaças activas",
    "Distribuição por severidade",
    "Top ameaças (score)",
    "Componentes mais críticos",
    "Fluxos mais críticos",
    "Temas dominantes",
    "Mitigação inicial",
    "**Postura:**",
]

_ENGLISH_LABELS = [
    "### Risk consolidation and executive cockpit",
    "**Active threats:**",
    "**Total score:**",
    "**Severity distribution:**",
    "**Top threats (score):**",
    "**Most critical components:**",
    "**Most critical flows:**",
    "**Dominant themes:**",
    "**Initial mitigation:**",
    "**Posture:**",
]


@pytest.fixture
def result() -> AnalysisResult:
    return analyze_document(load_document_from_yaml_path(_MODEL))


@pytest.mark.parametrize("label", _ENGLISH_LABELS)
def test_the_english_export_uses_english_labels(result: AnalysisResult, label: str) -> None:
    assert label in export_analysis_markdown(result, locale="en")


@pytest.mark.parametrize("label", _PORTUGUESE_LABELS)
def test_the_english_export_drops_the_portuguese_labels(result: AnalysisResult, label: str) -> None:
    assert label not in export_analysis_markdown(result, locale="en")


@pytest.mark.parametrize("label", _PORTUGUESE_LABELS)
def test_the_portuguese_export_is_unchanged(result: AnalysisResult, label: str) -> None:
    """The pt-BR wording is the shipped default and must not drift while fixing `en`."""
    assert label in export_analysis_markdown(result, locale="pt-BR")


def test_the_severity_distribution_is_not_a_python_repr(result: AnalysisResult) -> None:
    assert "{'" not in export_analysis_markdown(result, locale="en")


def test_the_severity_distribution_is_readable(result: AnalysisResult) -> None:
    markdown = export_analysis_markdown(result, locale="en")
    line = next(ln for ln in markdown.splitlines() if "Severity distribution" in ln)

    assert line.endswith("high: 25, medium: 1, critical: 1")


def test_the_block_sits_between_its_english_neighbours(result: AnalysisResult) -> None:
    """The section above it was already English, which is what made the defect so visible."""
    headings = [ln for ln in export_analysis_markdown(result, locale="en").splitlines() if ln.startswith("### ")]
    index = headings.index("### Risk consolidation and executive cockpit")

    assert headings[index - 1] == "### Framework references (aggregate)"
