"""A ligação ativo-componente também se declara dos dois lados, e a lente lia um só.

`Component.asset_ids` e `Asset.related_component_ids` dizem a mesma coisa, o schema valida as duas,
e `_components_holding_classified_data` — escrito antes neste ramo para pôr a lente NIST a ler o
documento — lê só a primeira.

Medido no mesmo modelo, escrito das duas formas permitidas:

    ligação declarada no ATIVO       0 afirmações de dados classificados
    ligação declarada no COMPONENTE  1 afirmação

É exactamente a classe que este ramo já corrigiu três vezes para as fronteiras de confiança, e é
uma correcção minha que ficou a meio: tratei o lado que faltava na lente e não vi que a própria
ligação tinha dois lados.

A resolução passa a ter um sítio, `resolve_component_assets`, ao lado da que já existe para as
fronteiras — para o próximo consumidor não reimplementar a regra e voltar a ler um lado só.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))


def _document(*, on_asset_side: bool):
    from otm_core_schema import ThreatModelDocument

    component = {"id": "svc", "name": "Servico", "kind": "process"}
    asset = {"id": "pii1", "name": "Registos de clientes", "asset_kind": "pii"}
    if on_asset_side:
        asset["related_component_ids"] = ["svc"]
    else:
        component["asset_ids"] = ["pii1"]
    return ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0"},
            "metadata": {"title": "Sistema", "tags": []},
            "components": [component, {"id": "db", "name": "Base", "kind": "datastore"}],
            "assets": [asset],
        }
    )


def _classified_claims(*, on_asset_side: bool) -> list[str]:
    from otm_threat_engine import analyze_document

    result = analyze_document(_document(on_asset_side=on_asset_side), methodology="nist_data_centric")
    return sorted(h.id for h in result.heuristic_threats if "classified_data" in h.id)


def test_o_lado_do_componente_ja_era_lido() -> None:
    """Premissa: é contra este resultado que o outro lado é comparado."""
    assert _classified_claims(on_asset_side=False) == ["nist_dc_classified_data_svc"]


def test_as_duas_formas_dao_o_mesmo_resultado() -> None:
    assert _classified_claims(on_asset_side=True) == _classified_claims(on_asset_side=False)


@pytest.mark.parametrize("on_asset_side", [True, False])
def test_o_resolvedor_devolve_a_mesma_pertenca(on_asset_side: bool) -> None:
    from otm_core_schema.asset_membership import resolve_component_assets

    assert resolve_component_assets(_document(on_asset_side=on_asset_side)) == {"svc": {"pii1"}}


def test_um_ativo_sem_ligacao_nao_pertence_a_ninguem() -> None:
    """A correcção não podia ser ligar tudo a tudo."""
    from otm_core_schema import ThreatModelDocument
    from otm_core_schema.asset_membership import resolve_component_assets

    document = ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0"},
            "metadata": {"title": "Sistema", "tags": []},
            "components": [{"id": "svc", "name": "Servico", "kind": "process"}],
            "assets": [{"id": "solto", "name": "Sem dono", "asset_kind": "data"}],
        }
    )

    assert resolve_component_assets(document) == {}


def test_as_duas_direccoes_somam_se() -> None:
    """Um componente pode ganhar ativos pelos dois lados; nenhum apaga o outro."""
    from otm_core_schema import ThreatModelDocument
    from otm_core_schema.asset_membership import resolve_component_assets

    document = ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0"},
            "metadata": {"title": "Sistema", "tags": []},
            "components": [{"id": "svc", "name": "Servico", "kind": "process", "asset_ids": ["a1"]}],
            "assets": [
                {"id": "a1", "name": "Um", "asset_kind": "data"},
                {"id": "a2", "name": "Dois", "asset_kind": "pii", "related_component_ids": ["svc"]},
            ],
        }
    )

    assert resolve_component_assets(document) == {"svc": {"a1", "a2"}}
