"""`ann` é uma palavra, e comparava-se como subcadeia.

`_KW_VECTOR` lista `"ann"` — *approximate nearest neighbour* — e passa por `has_any`, que compara
subcadeias. O mesmo ficheiro já tem `has_any_token` e usa-o exactamente para os dois casos com este
problema, `"llm"` e `"rag"`. O `"ann"` ficou de fora.

Medido, com `has_any` contra `_KW_VECTOR`:

    scanner  planner  banner  channel  annual  manner  canning   -> todos True

São nomes banais de componentes. Qualquer um deles num sistema de IA acendia `vector_embedding` e
fazia o PLOT4ai emitir ameaças de RAG e de armazenamento vectorial para um sistema que não tem
nenhum dos dois — e as ameaças fabricadas entram no relatório, no backlog e no SARIF com a mesma
aparência das reais.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

_INNOCENT = ["scanner", "planner", "banner", "channel", "annual", "manner", "canning"]


def _vector_signal(text: str) -> bool:
    from otm_threat_engine.ai_modeling.keyword_signal_apply import _KW_VECTOR
    from otm_threat_engine.methodology_lenses.common import has_any, has_any_token

    # minúsculas como o motor faz: `_corpus` normaliza antes de comparar.
    lowered = text.lower()
    return has_any(lowered, _KW_VECTOR) or has_any_token(lowered, ("ann",))


@pytest.mark.parametrize("word", _INNOCENT)
def test_uma_palavra_que_contem_ann_nao_e_um_vector_store(word: str) -> None:
    assert not _vector_signal(word), f"`{word}` acendeu o sinal de armazenamento vectorial"


@pytest.mark.parametrize("text", ["ann", "usa ANN para pesquisa", "índice ann"])
def test_a_palavra_ann_continua_a_contar(text: str) -> None:
    """A correcção não podia ser apagar o termo: `ann` é mesmo um sinal de vector store."""
    assert _vector_signal(text)


@pytest.mark.parametrize("term", ["faiss", "pinecone", "vector store", "embeddings"])
def test_os_outros_termos_do_grupo_continuam_a_contar(term: str) -> None:
    assert _vector_signal(term)


def _vector_threat_ids(extra_components: list[dict[str, str]]) -> set[str]:
    from otm_core_schema import ThreatModelDocument
    from otm_threat_engine import analyze_document

    document = ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0"},
            "metadata": {"title": "Assistente de conversa", "summary": "Chatbot com um LLM."},
            "components": [{"id": "bot", "name": "Chatbot LLM", "kind": "process"}, *extra_components],
        }
    )
    result = analyze_document(document, methodology="plot4ai")
    return {h.id for h in result.heuristic_threats if "vector" in h.id.lower() or "rag" in h.id.lower()}


def test_um_componente_chamado_scanner_nao_acrescenta_ameacas_de_rag() -> None:
    """Diferencial, e não absoluto: a asserção certa é que o `scanner` não acrescenta nada.

    A primeira versão exigia **zero** ameaças com `rag` no id, e falhava por causa de
    `plot4ai_rag_data_leakage` — que o motor emite para qualquer sistema com LLM, com ou sem o
    componente. Estava a acusar comportamento legítimo, e a asserção é que estava errada.
    """
    baseline = _vector_threat_ids([])
    with_scanner = _vector_threat_ids([{"id": "scanner", "name": "Scanner de documentos", "kind": "process"}])

    assert with_scanner == baseline, f"o `scanner` fabricou {sorted(with_scanner - baseline)}"
