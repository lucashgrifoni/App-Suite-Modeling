""""Graphics" não é informação de saúde protegida, e a lente de privacidade achava que sim.

`_looks_like_pii_context` compara os sinais de privacidade por subcadeia. `"phi"` — acrónimo de
*Protected Health Information* — mora dentro de **gra*phi*cs**, e também de *sophisticated*,
*philosophy* e *morphism*.

Medido, mudando só o nome de um componente:

    Graphics Engine   7 ameaças LINDDUN
    Render Engine     0 ameaças LINDDUN

Sete ameaças de privacidade num serviço de renderização, e a lente ainda apaga a ressalva de que
não há sinais de PII — a ressalva existe precisamente para o leitor saber que a análise foi feita
sem contexto.

Este é o mesmo ficheiro cuja leitura dos **ativos** foi corrigida antes neste ramo. Esta é a
leitura do **texto**, que ficou.

Os acrónimos pedem fronteira dos dois lados; os radicais deliberados, só à esquerda: `consent`
tem de continuar a apanhar *consentimento*. O modo é uma decisão por palavra.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))


def _linddun_threats(component_name: str, *, summary: str = "") -> int:
    from otm_core_schema import ThreatModelDocument
    from otm_threat_engine import analyze_document

    document = ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0"},
            "metadata": {"title": "Servico de render", "summary": summary, "tags": []},
            "components": [
                {"id": "svc", "name": component_name, "kind": "process"},
                {"id": "db", "name": "Base", "kind": "datastore"},
            ],
            "data_flows": [{"id": "f", "name": "grava", "from_component": "svc", "to_component": "db"}],
        }
    )
    result = analyze_document(document, methodology="linddun")
    return len([h for h in result.heuristic_threats if h.id.startswith("linddun")])


def test_um_componente_neutro_nao_produz_ameacas_de_privacidade() -> None:
    """Premissa: é contra esta linha de base que as outras são comparadas."""
    assert _linddun_threats("Render Engine") == 0


@pytest.mark.parametrize("name", ["Graphics Engine", "Sophisticated Router", "Morphism Service"])
def test_uma_palavra_que_contem_phi_nao_liga_a_lente(name: str) -> None:
    assert _linddun_threats(name) == 0, f"`{name}` ligou a lente de privacidade"


@pytest.mark.parametrize(
    ("name", "summary"),
    [
        ("PHI store", ""),
        ("Render Engine", "Guardamos PHI dos pacientes."),
        ("Render Engine", "Fluxo com consentimento explicito do titular."),
        ("Render Engine", "Sistema sujeito a LGPD."),
    ],
)
def test_o_sinal_de_privacidade_verdadeiro_continua_a_ligar(name: str, summary: str) -> None:
    """A correcção não podia ser calar a lente, nem partir o radical de `consent`."""
    assert _linddun_threats(name, summary=summary) > 0
