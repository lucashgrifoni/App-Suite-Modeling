"""A linha do componente no Markdown omitia a fronteira declarada do lado da fronteira.

`document_markdown.py:68` lê `c.in_trust_boundary` directamente. O schema aceita declarar a
pertença dos dois lados e `resolve_component_boundaries` existe para os juntar — foi o que uma
correcção anterior deste ramo ligou ao relatório premium e ao `diff_insights`. Este exportador
ficou de fora.

Medido no mesmo modelo escrito das duas formas:

    lado da fronteira    - **Web tier** (`web`) — process
    lado do componente   - **Web tier** (`web`) — process, fronteira `tb_dmz`

O documento exportado é o que alguém revê; a fronteira de confiança de um componente não pode
depender de qual das duas formas o autor escolheu.

**Metade do achado original é refutada, e fica registada:** o `parent.trustZone` do
`otm export -f otm` também só lê esse campo, mas a pertença **sobrevive** ao round-trip por outro
caminho — `resolve_component_boundaries` devolve `{'web': 'tb_dmz'}` antes e depois, porque os
`member_component_ids` da fronteira viajam nos trustZones. Aí não há perda, e não se mexe.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "exporters", "artifact-import", "industry-packs"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))


def _document(*, boundary_side: bool):
    from otm_core_schema import ThreatModelDocument

    components = [{"id": "web", "name": "Web tier", "kind": "process"}]
    boundaries = [{"id": "tb_dmz", "name": "DMZ", "boundary_scenario": "boundary_client_to_server"}]
    if boundary_side:
        boundaries[0]["member_component_ids"] = ["web"]
    else:
        components[0]["in_trust_boundary"] = "tb_dmz"
    return ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0"},
            "metadata": {"title": "t"},
            "components": components,
            "trust_boundaries": boundaries,
        }
    )


def _component_line(*, boundary_side: bool) -> str:
    from otm_exporters import export_document_markdown

    markdown = export_document_markdown(_document(boundary_side=boundary_side))
    return next(line for line in markdown.splitlines() if "Web tier" in line)


def test_a_forma_do_lado_do_componente_ja_mostrava_a_fronteira() -> None:
    """Premissa: é contra esta linha que a outra é comparada."""
    assert "tb_dmz" in _component_line(boundary_side=False)


def test_as_duas_formas_dao_a_mesma_linha() -> None:
    assert _component_line(boundary_side=True) == _component_line(boundary_side=False)


def test_um_componente_sem_fronteira_nao_ganha_uma() -> None:
    """A correcção não podia ser inventar pertença onde não há."""
    from otm_core_schema import ThreatModelDocument
    from otm_exporters import export_document_markdown

    document = ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0"},
            "metadata": {"title": "t"},
            # O nome não pode conter a palavra que a asserção procura -- a primeira versão
            # chamava-lhe "Sem fronteira" e falhava por causa do próprio nome.
            "components": [{"id": "solto", "name": "Servico isolado", "kind": "process"}],
        }
    )
    line = next(line for line in export_document_markdown(document).splitlines() if "Servico isolado" in line)

    assert "fronteira" not in line.lower()


@pytest.mark.parametrize("boundary_side", [True, False])
def test_a_pertenca_sobrevive_ao_round_trip_otm_nos_dois_casos(boundary_side: bool) -> None:
    """A metade refutada do achado, presa: aqui não há perda, e não se mexeu."""
    from otm_artifact_import.otm_native import document_to_otm, otm_to_document
    from otm_core_schema.trust_membership import resolve_component_boundaries

    document = _document(boundary_side=boundary_side)
    back = otm_to_document(document_to_otm(document))

    assert resolve_component_boundaries(back) == resolve_component_boundaries(document)
