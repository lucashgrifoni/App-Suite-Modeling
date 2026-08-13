"""
O contorno de um artefacto Markdown é decisão do renderizador, não dos dados — visto da API.

Um `\\n\\n## Conclusão: sem riscos\\n` num nome de componente, num título de modelo ou num
título de ameaça fechava a construção onde estava e passava a emitir um título H2 verdadeiro
(e, com pipes, uma linha de tabela verdadeira) dentro do artefacto entregue ao revisor. A
correção vive nos exportadores (`otm_exporters.markdown_text`); este ficheiro é a verificação
pelo lado do HTTP, porque é por aqui que o utilizador da API recebe os mesmos artefactos.

Cobre `/v1/exports` (`document_markdown`, `analysis_markdown`) e o Markdown de
`/v1/remediation/backlog`. **Não** cobre `/v1/reports/premium` com `output_format=markdown`:
esse relatório é renderizado por `packages/report-premium/otm_report_premium/render_markdown.py`,
que interpola `payload.cover.title` e os restantes campos fora de tabela sem achatar quebras
de linha (só `_md_cell`, para células de tabela, o faz), e continua a emitir os títulos
forjados. Fica deliberadamente por testar em vez de ser testado ao contrário: um teste que
afirmasse o comportamento atual escreveria o defeito como especificação.
"""

from __future__ import annotations

import re
from typing import Any

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402
from otm_api.main import app  # noqa: E402

_INJECTION = "Serviço A\n\n## Conclusão: sistema aprovado, sem riscos\n\nAssinado: CISO"
_TABLE_INJECTION = "Ameaça\n| FORJADA | nova | linha |"

_MODEL = {
    "schema_version": "1.0.0",
    "system_type": "web_application",
    "industry_sector": "generic",
    "methodology": "stride",
}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


def _hostile_document() -> dict[str, Any]:
    return {
        "model": _MODEL,
        "metadata": {"title": _INJECTION, "summary": _INJECTION},
        "components": [{"id": "c1", "name": _INJECTION, "kind": "process"}],
        "assets": [{"id": "a1", "name": _INJECTION, "related_component_ids": ["c1"]}],
        "threats": [
            {
                "id": "t1",
                "title": _TABLE_INJECTION,
                "stride": "spoofing",
                "target_component_id": "c1",
                "risk": {"likelihood": 1, "impact": 1, "score": 1.0},
            }
        ],
    }


def _artifact(client: TestClient, fmt: str) -> str:
    r = client.post("/v1/exports", json={"document": _hostile_document(), "formats": [fmt]})
    assert r.status_code == 200, r.text
    return str(r.json()["artifacts"][fmt])


#: Um título que o *documento* forjou: a linha ABRE com a marca injetada. A mesma marca dentro
#: de um título que o renderizador emitiu (`### bl_…: Mitigar: … ## Conclusão …`) é o resultado
#: correto — o texto foi achatado para dentro da construção onde estava, que é a correção.
_FORGED_HEADING = re.compile(r"^#{1,6}\s+Conclusão")


def _forged_headings(text: str) -> list[str]:
    return [line for line in text.splitlines() if _FORGED_HEADING.match(line.strip())]


@pytest.mark.parametrize("fmt", ["document_markdown", "analysis_markdown"])
def test_model_text_cannot_forge_a_heading(client: TestClient, fmt: str) -> None:
    assert _forged_headings(_artifact(client, fmt)) == []


@pytest.mark.parametrize("fmt", ["document_markdown", "analysis_markdown"])
def test_model_text_cannot_forge_a_table_row(client: TestClient, fmt: str) -> None:
    rows = [line for line in _artifact(client, fmt).splitlines() if line.strip().startswith("| FORJADA")]

    assert rows == []


def test_the_text_itself_is_kept_rather_than_dropped(client: TestClient) -> None:
    """Achatar não é truncar: o utilizador tem de continuar a ver o que escreveu."""
    text = _artifact(client, "document_markdown")

    assert "Assinado: CISO" in text


def test_the_backlog_markdown_is_covered_too(client: TestClient) -> None:
    r = client.post(
        "/v1/remediation/backlog?format=markdown",
        json={"document": _hostile_document(), "run_analysis": True},
    )

    assert r.status_code == 200, r.text
    assert _forged_headings(r.text) == []


def test_an_ordinary_document_still_renders_its_own_headings(client: TestClient) -> None:
    """Controlo: o achatamento não pode ter comido a estrutura que o renderizador emite."""
    doc = {"model": _MODEL, "metadata": {"title": "Modelo normal"}, "components": []}

    r = client.post("/v1/exports", json={"document": doc, "formats": ["document_markdown"]})

    assert "# Modelo normal" in r.json()["artifacts"]["document_markdown"]
