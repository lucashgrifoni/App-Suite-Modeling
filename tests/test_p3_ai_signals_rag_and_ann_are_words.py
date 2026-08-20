""""Object Storage" e "Scanner" armavam juntos o sinal de RAG/vector store.

A condição exige dois sinais independentes — um de retrieval **e** um de vector — precisamente para
não disparar por acaso. Comparados por subcadeia, um único par de nomes banais satisfaz os dois:
*sto**rag**e* satisfaz o primeiro, *sc**ann**er* o segundo.

    componentes "Object Storage" + "Scanner"
      primeira condição  -> True   (por causa de storage)
      segunda condição   -> True   (por causa de scanner)
      sinal armado       -> True

Quarto ficheiro com este par exacto nesta campanha, depois de `keyword_signal_apply`, de
`classify` e da biblioteca de anti-padrões. `rag` e `ann` são acrónimos e pedem fronteira dos dois
lados; os termos longos da mesma lista ficam como estão.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))


def _vector_signal(component_names: list[str]) -> bool:
    from otm_core_schema import ThreatModelDocument
    from otm_threat_engine.ai_modeling.signals import collect_ai_signals_from_document

    document = ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0"},
            "metadata": {"title": "Assistente", "summary": "Servico com um LLM.", "tags": []},
            "components": [
                {"id": f"c{i}", "name": name, "kind": "process"} for i, name in enumerate(component_names)
            ],
        }
    )
    return bool(collect_ai_signals_from_document(document).vector_embedding)


@pytest.mark.parametrize(
    "names",
    [
        ["Object Storage", "Scanner"],
        ["Storage bucket", "Planner"],
        ["Fragmento de sessao", "Banner service"],
    ],
)
def test_nomes_banais_nao_armam_o_sinal_de_vector_store(names: list[str]) -> None:
    assert not _vector_signal(names), f"{names} armaram o sinal de RAG/vector store"


def test_o_lado_do_ann_sozinho_tambem_e_apanhado() -> None:
    """Um sinal genuíno de um lado e uma colisão banal do outro.

    A primeira versão só apanhava a regressão **conjunta**: mutando apenas `rag` ou apenas `ann`, o
    `and` protegia e o teste ficava verde. Este caso dá retrieval genuíno e `Scanner` do outro
    lado, portanto falha se o `ann` sozinho voltar a comparar-se por subcadeia.

    O lado do `rag` **não** tem um caso equivalente, e isso fica dito em vez de fingido: tudo o que
    satisfaz a segunda condição — `vector`, `embedding`, `similarity` — arma o sinal por si só pelo
    caminho das palavras-chave, medido. Um "Object Storage" ao lado de um "Vector database" arma
    legitimamente, por causa do segundo. Só a colisão dupla é observável nesse lado.
    """
    assert not _vector_signal(["Retrieval service", "Scanner"])


@pytest.mark.parametrize(
    "names",
    [
        ["RAG pipeline", "ANN index"],
        ["Retrieval service", "Vector database"],
        ["Chunk splitter", "Embedding store"],
    ],
)
def test_o_sinal_verdadeiro_continua_a_armar(names: list[str]) -> None:
    """A correcção não podia ser desligar o sinal."""
    assert _vector_signal(names)
