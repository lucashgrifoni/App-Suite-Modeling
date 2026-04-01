from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_core_schema.enums import IndustrySector, StrideCategory
from otm_industry_packs.models import AdditionalThreatRule, PackDefinition, RiskTuning
from otm_threat_engine.pack_runtime import apply_pack_to_li, iter_pack_heuristic_threats

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def _sample_pack() -> PackDefinition:
    return PackDefinition(
        id="financepack",
        name="Finance Pack",
        sector=IndustrySector.FINANCE,
        risk_tuning=RiskTuning(likelihood_multiplier=1.2, impact_multiplier=1.3),
        additional_threats=[
            AdditionalThreatRule(
                id="ruleA",
                title="Financial abuse",
                stride=StrideCategory.TAMPERING,
                likelihood_delta=1,
                impact_delta=1,
            )
        ],
    )


def test_apply_pack_to_li_clamps_bounds() -> None:
    pack = _sample_pack()
    low = apply_pack_to_li(1, 1, pack)
    high = apply_pack_to_li(5, 5, pack)
    assert 1 <= low[0] <= 5 and 1 <= low[1] <= 5
    assert 1 <= high[0] <= 5 and 1 <= high[1] <= 5


def test_iter_pack_heuristics_marks_duplicate_when_covered() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    comp_id = doc.components[0].id
    covered = {(comp_id, None, StrideCategory.TAMPERING.value)}
    pack = _sample_pack()
    out, skipped = iter_pack_heuristic_threats(doc, pack, covered)
    assert out
    assert skipped >= 1
    assert any(h.skipped_as_duplicate for h in out)


def test_iter_pack_heuristics_adds_non_duplicate_when_not_covered() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    covered: set[tuple[str | None, str | None, str]] = set()
    pack = _sample_pack()
    out, skipped = iter_pack_heuristic_threats(doc, pack, covered)
    assert out
    assert skipped == 0
    assert any(not h.skipped_as_duplicate for h in out)


def test_iter_pack_heuristics_deduplicates_repeated_rules_per_component() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    pack = _sample_pack().model_copy(
        update={"additional_threats": [*_sample_pack().additional_threats] * 2}
    )
    covered: set[tuple[str | None, str | None, str]] = set()
    out, skipped = iter_pack_heuristic_threats(doc, pack, covered)
    assert out
    assert skipped == 0
    # Mesmo rule.id repetido no pack não deve emitir duplicado no mesmo componente.
    ids = [h.id for h in out]
    assert len(ids) == len(set(ids))


def test_iter_pack_heuristics_adds_default_description_when_rule_missing_description() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    pack = _sample_pack()
    covered: set[tuple[str | None, str | None, str]] = set()
    out, _skipped = iter_pack_heuristic_threats(doc, pack, covered)
    assert out
    # Nosso sample_pack não define description; deve gerar mensagem default com pack.name.
    assert any(pack.name in h.description for h in out)
