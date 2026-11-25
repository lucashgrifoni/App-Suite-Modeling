"""Declarar dados pessoais com mais precisão não pode desligar a lente de privacidade.

`_looks_like_pii_context` aceitava um ativo só quando `asset_kind == "data"` **e** o campo legado
`sensitivity` era confidential/restricted. O schema tem, para a mesma coisa, dois campos mais
precisos: `AssetKind.PII` — o valor dedicado a dados pessoais — e `data_classification`, que o
próprio `document.py` descreve como a classificação explícita enquanto chama a `sensitivity`
*"texto livre legado"*.

Medido nas quatro combinações, antes da correcção, no mesmo documento sem palavra nenhuma de
privacidade no texto:

    asset_kind=pii  + data_classification=restricted   0 ameaças
    asset_kind=pii  + sensitivity=restricted           0 ameaças
    asset_kind=data + data_classification=restricted   0 ameaças
    asset_kind=data + sensitivity=restricted           7 ameaças + 4 recomendações

Só a forma legada funcionava. Um modelador que declare `pii` — o valor certo — perde a lente
inteira, e o motor continua a recomendar LINDDUN com confiança alta, a imprimir "Lente LINDDUN
aplicada" e a escrever na evidência que não há sinais de PII nos ativos.

`AssetKind.PII` já não era usado em lado nenhum da lógica do motor, apesar de `MODELING_QUALITY.md`
o oferecer ao modelador. Esta é a mesma classe que o projecto já corrigiu para o PLOT4ai — ver o
docstring de `otm_core_schema/ai_context.py`: *"uma definição, um sítio"*.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings", "exporters"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))


def _analyse(asset: dict[str, Any]) -> tuple[int, int]:
    """(ameaças LINDDUN, recomendações) para um documento sem pistas textuais de privacidade."""
    from otm_core_schema import ThreatModelDocument
    from otm_threat_engine import analyze_document

    document = ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0"},
            "metadata": {"title": "Sistema de encomendas", "tags": []},
            "components": [
                {"id": "svc", "name": "Servico", "kind": "process"},
                {"id": "store", "name": "Base", "kind": "datastore"},
            ],
            "data_flows": [{"id": "f", "name": "grava", "from_component": "svc", "to_component": "store"}],
            "assets": [dict({"id": "a1", "name": "Registos de clientes"}, **asset)],
        }
    )
    result = analyze_document(document, methodology="linddun")
    threats = len([h for h in result.heuristic_threats if h.id.startswith("linddun")])
    recommendations = len([f for f in result.structural_findings if "LINDDUN_REC" in str(getattr(f, "code", ""))])
    return threats, recommendations


def test_a_forma_legada_continua_a_activar_a_lente() -> None:
    """Não-regressão: era a única que funcionava, e tem de continuar a funcionar."""
    threats, recommendations = _analyse({"asset_kind": "data", "sensitivity": "restricted"})

    assert threats > 0 and recommendations > 0


@pytest.mark.parametrize(
    "asset",
    [
        {"asset_kind": "pii"},
        {"asset_kind": "pii", "data_classification": "restricted"},
        {"asset_kind": "pii", "sensitivity": "restricted"},
        {"asset_kind": "data", "data_classification": "restricted"},
        {"asset_kind": "data", "data_classification": "confidential"},
    ],
    ids=["pii", "pii+dc", "pii+legado", "data+dc-restricted", "data+dc-confidential"],
)
def test_as_formas_precisas_activam_a_lente(asset: dict[str, Any]) -> None:
    threats, recommendations = _analyse(asset)

    assert threats > 0, f"nenhuma ameaça de privacidade para um ativo declarado {asset}"
    assert recommendations > 0, f"nenhuma recomendação LINDDUN para {asset}"


@pytest.mark.parametrize(
    "asset",
    [
        {"asset_kind": "data"},
        {"asset_kind": "data", "data_classification": "public"},
        {"asset_kind": "data", "data_classification": "internal"},
        {"asset_kind": "service"},
    ],
    ids=["sem classificacao", "publico", "interno", "servico"],
)
def test_um_ativo_sem_sinal_de_privacidade_nao_activa_a_lente(asset: dict[str, Any]) -> None:
    """A correcção não podia ser ligar a lente sempre: isso encheria de ruído modelos sem PII."""
    threats, _ = _analyse(asset)

    assert threats == 0, f"ameaças de privacidade num ativo sem sinal nenhum: {asset}"
