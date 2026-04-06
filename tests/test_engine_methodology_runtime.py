from pathlib import Path

from otm_core_schema import Metadata, load_document_from_yaml_path
from otm_core_schema.enums import ThreatModelMethodology
from otm_threat_engine.engine_methodology_runtime import resolve_methodology_selection

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_resolve_methodology_prefers_explicit_parameter() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(update={"metadata": Metadata(title="LLM RAG com agentes")})
    chosen, reason, exps = resolve_methodology_selection(
        doc,
        methodology=ThreatModelMethodology.CIA_DIE,
        auto_recommend=True,
    )
    assert chosen == ThreatModelMethodology.CIA_DIE
    assert reason is None
    assert exps == ()


def test_resolve_methodology_uses_auto_recommend_when_no_explicit() -> None:
    doc = load_document_from_yaml_path(_MINIMAL).model_copy(update={"metadata": Metadata(title="LLM RAG com agentes")})
    chosen, reason, exps = resolve_methodology_selection(
        doc,
        methodology=None,
        auto_recommend=True,
    )
    assert chosen == ThreatModelMethodology.PLOT4AI
    assert reason is not None
    assert len(exps) >= 1


def test_resolve_methodology_accepts_string_enum_value() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    chosen, reason, exps = resolve_methodology_selection(
        doc,
        methodology="linddun",
        auto_recommend=True,
    )
    assert chosen == ThreatModelMethodology.LINDDUN
    assert reason is None
    assert exps == ()


def test_resolve_methodology_falls_back_to_document_when_no_explicit() -> None:
    base = load_document_from_yaml_path(_MINIMAL)
    doc = base.model_copy(
        update={"model_info": base.model_info.model_copy(update={"methodology": ThreatModelMethodology.PASTA})}
    )
    chosen, reason, exps = resolve_methodology_selection(
        doc,
        methodology=None,
        auto_recommend=False,
    )
    assert chosen == ThreatModelMethodology.PASTA
    assert reason is None
    assert exps == ()
