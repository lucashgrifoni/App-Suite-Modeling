"""Critérios sobre campos de lista (`asset_ids`, `data_types`, `related_component_ids`).

A documentação anuncia estes campos como casáveis e o loader aceita-os sem queixa, por isso o
único modo de falha possível era o pior: a regra existe, o `otm analyze` sai 0, e nunca casa
nada. É a mesma falha silenciosa que `_reject_unknown` foi escrito para impedir nos campos
escritos com erro.
"""

from __future__ import annotations

from pathlib import Path

from otm_core_schema import load_document_from_yaml_path
from otm_threat_engine.custom_rules import CustomRuleSet, iter_custom_rule_threats
from otm_threat_engine.custom_rules.runtime import _criterion_matches

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"

_RULES = {
    "id": "acme",
    "rules": [
        {
            "id": "asset_scalar",
            "title": "Componente que toca em orders_data",
            "stride": "information_disclosure",
            "match": {"component": {"asset_ids": "orders_data"}},
        },
        {
            "id": "asset_list",
            "title": "Componente que toca em orders_data ou noutro",
            "stride": "information_disclosure",
            "match": {"component": {"asset_ids": ["orders_data", "nao_existe"]}},
        },
        {
            "id": "asset_links",
            "title": "Ativo ligado ao componente api",
            "stride": "information_disclosure",
            "match": {"asset": {"related_component_ids": ["api"]}},
        },
    ],
}


def _fired() -> tuple[set[str], set[str]]:
    doc = load_document_from_yaml_path(_MINIMAL)
    threats, fired = iter_custom_rule_threats(doc, CustomRuleSet.model_validate(_RULES))
    targets = {t.target_component_id or t.target_asset_id or "" for t in threats}
    return fired, targets


def test_scalar_criterion_matches_a_member_of_a_list_field() -> None:
    # `api` e `db` declaram `asset_ids: [orders_data]`.
    assert _criterion_matches(["orders_data"], "orders_data") is True
    assert _criterion_matches(["a", "b"], "a") is True
    assert _criterion_matches(["a", "b"], "c") is False


def test_list_criterion_is_any_of_these_against_a_list_field() -> None:
    assert _criterion_matches(["a", "b"], ["c", "b"]) is True
    assert _criterion_matches(["a", "b"], ["c", "d"]) is False


def test_scalar_fields_keep_plain_equality() -> None:
    assert _criterion_matches("datastore", "datastore") is True
    assert _criterion_matches("datastore", ["process", "datastore"]) is True
    assert _criterion_matches("datastore", "process") is False
    assert _criterion_matches(None, None) is True


def test_list_field_rules_actually_fire_end_to_end() -> None:
    fired, targets = _fired()
    assert fired == {"asset_scalar", "asset_list", "asset_links"}
    # api e db partilham orders_data; orders_data está ligado a api.
    assert {"api", "db", "orders_data"} <= targets
