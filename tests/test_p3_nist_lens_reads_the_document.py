"""A lente data-centric tem de olhar para a classificação dos dados do documento.

`apply_nist_data_centric_lens` recebia só o `AnalysisResult` — o despachante passa-lhe o documento
e ela descartava-o com `_ = doc`. Decidia "componente sensível" a partir do texto e do score das
heurísticas STRIDE já existentes (`score >= 12.0`), o que não é uma leitura dos dados: é uma
reetiquetagem da severidade STRIDE.

Medido antes da correcção, três documentos com os mesmos componentes e fluxos:

    um ativo tudo público      6 ameaças NIST
    sem ativos nenhuns         6 ameaças NIST
    um ativo restrito          6 ameaças NIST

As mesmas seis, byte a byte. A saída era independente da classificação dos dados, que é a única
coisa que "data-centric" quer dizer — e uma delas, `nist_dc_classified_data_visitante`, afirmava
dados classificados num componente `kind: user`, ou seja, numa pessoa.

A correcção **intersecta** com o sinal antigo em vez de o substituir: só pode retirar afirmações
que o documento não sustenta, nunca acrescentar ameaças novas. Os 38 templates distribuídos
declaram todos pelo menos um ativo sensível e ligam-no a componentes, por isso o corpus real
mantém-se.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

_PUBLIC_ASSET = {
    "id": "horarios",
    "name": "Horarios",
    "asset_kind": "data",
    "sensitivity": "public",
    "data_classification": "public",
}
_RESTRICTED_ASSET = {"id": "clientes", "name": "Clientes", "asset_kind": "data", "data_classification": "restricted"}


def _nist_threat_ids(assets: list[dict[str, Any]], *, link_to: str | None = None) -> list[str]:
    from otm_core_schema import ThreatModelDocument
    from otm_threat_engine import analyze_document

    portal: dict[str, Any] = {"id": "portal", "name": "Portal", "kind": "process"}
    if link_to:
        portal["asset_ids"] = [link_to]
    document = ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0"},
            "metadata": {"title": "Portal de horarios", "tags": []},
            "components": [
                {"id": "visitante", "name": "Visitante", "kind": "user"},
                portal,
                {"id": "cache", "name": "Cache", "kind": "datastore"},
            ],
            "data_flows": [
                {
                    "id": "visita",
                    "name": "consulta",
                    "from_component": "visitante",
                    "to_component": "portal",
                    "protocol": "HTTPS",
                    "encrypted": True,
                    "authenticated": True,
                }
            ],
            "assets": assets,
        }
    )
    result = analyze_document(document, methodology="nist_data_centric")
    return sorted(h.id for h in result.heuristic_threats if h.id.startswith("nist_dc"))


def test_um_documento_todo_publico_nao_afirma_dados_classificados() -> None:
    classified = [i for i in _nist_threat_ids([_PUBLIC_ASSET]) if "classified_data" in i]

    assert not classified, f"dados classificados afirmados num modelo cujo único ativo é público: {classified}"


def test_um_documento_sem_ativos_nao_afirma_dados_classificados() -> None:
    classified = [i for i in _nist_threat_ids([]) if "classified_data" in i]

    assert not classified, f"dados classificados afirmados num documento sem ativos: {classified}"


def test_nunca_afirma_dados_classificados_numa_pessoa() -> None:
    """`kind: user` é uma pessoa; um componente-pessoa não armazena dados classificados."""
    for assets, link in (([_PUBLIC_ASSET], None), ([_RESTRICTED_ASSET], "clientes")):
        ids = _nist_threat_ids(assets, link_to=link)
        assert "nist_dc_classified_data_visitante" not in ids, ids


def test_o_documento_que_declara_dados_restritos_continua_a_ser_visto() -> None:
    """A correcção não podia ser calar a lente: o caso legítimo tem de continuar a produzir."""
    ids = _nist_threat_ids([_RESTRICTED_ASSET], link_to="clientes")

    assert any("classified_data_portal" in i for i in ids), ids


def test_a_saida_deixa_de_ser_a_mesma_para_documentos_diferentes() -> None:
    """A premissa do defeito: antes, os três davam exactamente o mesmo conjunto."""
    public = _nist_threat_ids([_PUBLIC_ASSET])
    empty = _nist_threat_ids([])
    restricted = _nist_threat_ids([_RESTRICTED_ASSET], link_to="clientes")

    assert public == empty, "público e vazio podem coincidir — nenhum declara dados sensíveis"
    assert restricted != public, "um documento com dados restritos tem de produzir algo diferente"
