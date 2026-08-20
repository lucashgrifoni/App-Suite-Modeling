""" "Object Storage" não é um sistema de IA, e o backlog classificava-o como tal.

`_ai_context` decidia por subcadeia sobre `("llm", "modelo de linguagem", "prompt", "rag",
"inferen")`. `rag` está dentro de **storage**, de **fragmento** e de **drag and drop**.

Medido:

    object storage   subcadeia=True   token=False
    storage bucket   subcadeia=True   token=False
    fragmento        subcadeia=True   token=False
    drag and drop    subcadeia=True   token=False
    rag pipeline     subcadeia=True   token=True
    usa RAG          subcadeia=True   token=True

`_ai_context` decide a categoria do item no backlog de remediação, e com ela o dono a quem o
trabalho é encaminhado: um bucket S3 chamado "Object Storage" ia para a equipa de plataforma de ML.
Terceira vez que esta classe aparece nesta campanha, depois de `ann` e de `edge` em `Ledger`; o
projecto tem `has_any_token` precisamente para os termos curtos.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))


def _is_ai(title: str) -> bool:
    from otm_core_schema import ThreatModelMethodology
    from otm_threat_engine.remediation.classify import _ai_context
    from otm_threat_engine.result import HeuristicThreat

    threat = HeuristicThreat.model_validate(
        {
            "id": "t1",
            "title": title,
            "description": "",
            "stride": "information_disclosure",
            "risk": {"likelihood": 3, "impact": 3},
        }
    )
    return _ai_context(ThreatModelMethodology.STRIDE, threat)


@pytest.mark.parametrize(
    "title",
    ["Object Storage exposto", "Storage bucket público", "Fragmento de sessão", "Drag and drop sem validação"],
)
def test_uma_palavra_que_contem_rag_nao_e_contexto_de_ia(title: str) -> None:
    assert not _is_ai(title), f"`{title}` classificado como contexto de IA"


@pytest.mark.parametrize(
    "title",
    ["RAG pipeline sem grounding", "O serviço usa RAG", "LLM gateway sem limites", "Inferência não autenticada"],
)
def test_o_contexto_de_ia_verdadeiro_continua_a_contar(title: str) -> None:
    assert _is_ai(title)


def test_a_metodologia_plot4ai_continua_a_bastar() -> None:
    """O atalho existe e não pode ser perdido: em PLOT4ai tudo é contexto de IA."""
    from otm_core_schema import ThreatModelMethodology
    from otm_threat_engine.remediation.classify import _ai_context
    from otm_threat_engine.result import HeuristicThreat

    threat = HeuristicThreat.model_validate(
        {
            "id": "t1",
            "title": "Object Storage exposto",
            "description": "",
            "stride": "information_disclosure",
            "risk": {"likelihood": 3, "impact": 3},
        }
    )

    assert _ai_context(ThreatModelMethodology.PLOT4AI, threat) is True
