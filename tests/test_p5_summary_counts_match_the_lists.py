"""O sumário conta o que está na lista ao lado dele, depois de a lente metodológica correr.

`AnalysisSummary` diz de si próprio "Totais para dashboards e relatórios rápidos", e é isso que o
painel do CLI, o Markdown e a UI imprimem. `structural_findings` é contado **antes** da lente, e
`recompute_summary_with_methodology` — que existe exactamente para reparar a deriva pós-lente —
actualiza cinco campos e salta este.

As lentes só mexem nesta lista (`common.py`, `linddun`, `nist_data_centric`, `pasta`, `plot4ai`,
todas via `model_copy(update={"structural_findings": ...})`), por isso o contador fica no valor
pré-lente e a mesma execução do `otm analyze` escreve as duas coisas:

    | Structural warnings: 0 |          e no JSON da mesma corrida: 8 entradas
    - Avisos estruturais: 0            seguido de `### Avisos estruturais` a listá-los

Medido em 60 sementes × 7 metodologias: seis das sete divergem em todas as 60 (`stride` não, porque
a sua lente não acrescenta nada), e 11 dos templates distribuídos divergem também.

A invariante é a mais simples que há: o número ao lado da lista é o tamanho da lista.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

_METHODOLOGIES = (
    "stride",
    "linddun",
    "pasta",
    "nist_data_centric",
    "octave_allegro",
    "cia_die",
    "plot4ai",
)


def _analyze(methodology: str) -> Any:
    from otm_core_schema import ThreatModelDocument
    from otm_threat_engine import analyze_document

    document = ThreatModelDocument.model_validate(
        {
            "model": {
                "schema_version": "1.1.0",
                "system_type": "web_application",
                "industry_sector": "healthcare",
                "methodology": methodology,
            },
            "metadata": {"title": "Portal clínico"},
            "components": [
                {"id": "c0", "name": "Portal de pacientes", "kind": "process"},
                {"id": "db", "name": "Registos clínicos", "kind": "datastore"},
            ],
            "data_flows": [{"id": "f0", "name": "Consulta", "from_component": "c0", "to_component": "db"}],
            "assets": [{"id": "a0", "name": "Dados clínicos do paciente", "asset_kind": "data"}],
        }
    )
    return analyze_document(document)


def test_pelo_menos_uma_lente_acrescenta_achados_estruturais() -> None:
    """Premissa: sem isto, a igualdade seria trivialmente verdadeira."""
    counts = {m: len(_analyze(m).structural_findings) for m in _METHODOLOGIES}

    assert max(counts.values()) > 0, f"nenhuma lente produziu achados estruturais: {counts}"


def test_o_sumario_conta_os_achados_estruturais_que_a_analise_devolve() -> None:
    wrong = {
        m: (r.summary.structural_findings, len(r.structural_findings))
        for m in _METHODOLOGIES
        if (r := _analyze(m)).summary.structural_findings != len(r.structural_findings)
    }

    assert not wrong, f"metodologia -> (sumário, tamanho da lista): {wrong}"


def test_o_sumario_conta_os_achados_de_trust_boundary() -> None:
    """O outro campo que a recontagem saltava, pela mesma razão."""
    wrong = {
        m: (r.summary.trust_boundary_findings, len(r.trust_boundary_findings))
        for m in _METHODOLOGIES
        if (r := _analyze(m)).summary.trust_boundary_findings != len(r.trust_boundary_findings)
    }

    assert not wrong, f"metodologia -> (sumário, tamanho da lista): {wrong}"


def test_os_contadores_de_heuristicas_continuam_disjuntos() -> None:
    """Âncora: a divisão base/pack que a recontagem já protegia não pode partir-se."""
    for m in _METHODOLOGIES:
        r = _analyze(m)
        s = r.summary
        total = (
            s.heuristic_threats_generated
            + s.heuristic_threats_skipped_duplicate
            + s.pack_threats_generated
            + s.pack_threats_skipped_duplicate
        )
        assert total == len(r.heuristic_threats), f"{m}: {total} != {len(r.heuristic_threats)}"
