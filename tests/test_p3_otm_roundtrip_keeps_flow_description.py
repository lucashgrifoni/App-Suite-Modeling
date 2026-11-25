"""O formato de intercâmbio não pode perder a descrição que o modelador escreveu no fluxo.

`otm export -f otm` é o formato de intercâmbio do produto, e o round-trip destruía silenciosamente
`DataFlow.description`. O defeito é uma omissão de uma linha, e os dois lados do mesmo módulo
discordavam entre si:

* `_DATAFLOW_OTM_SLOTS` **inclui** `"description"`, o que a exclui dos `attributes` por ser tratada
  como campo próprio — mas `_dataflows_to_otm` nunca escrevia esse campo. Caía entre os dois.
* `otm_to_document` já lê `description=df.get("description")`: o importador esperava-a.
* `_components_to_otm` escreve-a (`if c.description: comp["description"] = ...`). Só os fluxos não.

O que está provado: a descrição desaparece, e com ela muda estado do motor — `_corpus` lê
`f.description` e `_has_payment_anchor` passa de `True` para `False` num documento cuja única
menção a pagamento vive na descrição do fluxo.

O que **não** está provado, e por isso não se afirma: que isso mude a saída visível. Procurei um
documento em que os `control_hints` do pack mudassem por causa disso e não o encontrei. A perda de
um campo escrito pelo utilizador, num formato cujo propósito é transportá-lo, basta como defeito.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "artifact-import", "industry-packs", "framework-mappings"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

_DESCRIPTION = "Envia a autorizacao de pagamento ao PSP no checkout."


def _document(with_description: bool = True):
    from otm_core_schema import ThreatModelDocument

    flow = {"id": "f1", "name": "envio", "from_component": "svc", "to_component": "store"}
    if with_description:
        flow["description"] = _DESCRIPTION
    return ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0", "industry_sector": "finance"},
            "metadata": {"title": "Sistema de encomendas"},
            "components": [
                {"id": "svc", "name": "Servico", "kind": "process", "description": "Processa pedidos."},
                {"id": "store", "name": "Base", "kind": "datastore"},
            ],
            "data_flows": [flow],
        }
    )


def _roundtrip(doc):
    from otm_artifact_import.otm_native import document_to_otm, otm_to_document

    return otm_to_document(document_to_otm(doc))


def test_a_descricao_do_componente_ja_sobrevivia() -> None:
    """Premissa: o defeito é dos fluxos, não do round-trip inteiro."""
    assert _roundtrip(_document()).components[0].description == "Processa pedidos."


def test_a_descricao_do_fluxo_sobrevive_ao_round_trip() -> None:
    assert _roundtrip(_document()).data_flows[0].description == _DESCRIPTION


def test_o_campo_e_escrito_no_otm_exportado() -> None:
    """O importador já o lia; era o exportador que nunca o escrevia."""
    from otm_artifact_import.otm_native import document_to_otm

    assert document_to_otm(_document())["dataflows"][0].get("description") == _DESCRIPTION


def test_um_fluxo_sem_descricao_nao_ganha_o_campo() -> None:
    """Não escrever `description: null` — os exemplos distribuídos não podem mudar de bytes."""
    from otm_artifact_import.otm_native import document_to_otm

    assert "description" not in document_to_otm(_document(with_description=False))["dataflows"][0]


def test_o_estado_do_motor_deixa_de_mudar_no_round_trip() -> None:
    """`_corpus` lê a descrição do fluxo; perdê-la virava a âncora de pagamento."""
    from otm_threat_engine.recommendation_gate import _has_payment_anchor

    doc = _document()
    assert _has_payment_anchor(doc) is True, "premissa: a âncora só existe pela descrição"
    assert _has_payment_anchor(_roundtrip(doc)) is True
