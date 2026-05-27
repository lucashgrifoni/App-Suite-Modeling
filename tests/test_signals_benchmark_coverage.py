"""Coverage — AI signal bundle compat properties + benchmark coverage path."""

from __future__ import annotations

from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_threat_engine import analyze_document
from otm_threat_engine.ai_modeling.signals import AiSignalBundle
from otm_threat_engine.benchmark_metrics import compute_benchmark_metrics

_ROOT = Path(__file__).resolve().parents[1]


def test_ai_signal_bundle_compat_properties() -> None:
    b = AiSignalBundle(prompt_input=True, retrieval_grounding=True, agent_tool=True, ml_pipeline_referenced=True)
    assert b.prompting is True
    assert b.retrieval is True
    assert b.agent_actions is True
    assert b.governance_pipeline is True


def test_benchmark_metrics_with_expected_prefixes() -> None:
    doc = load_document_from_yaml_path(_ROOT / "examples" / "saas-ordering-v1.otm.yaml")
    analysis = analyze_document(doc)
    # active heuristics present -> the expected_stride_prefixes coverage block executes
    metrics = compute_benchmark_metrics(analysis, expected_stride_prefixes=("stride_", "cmp_"))
    assert metrics is not None
