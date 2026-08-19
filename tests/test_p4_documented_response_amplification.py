"""O número que dimensiona o limite de corpo do gateway tem de ser o número medido.

`docs/features/API.md` publica a amplificação de resposta e diz explicitamente para que serve:
escolher o limite de corpo do gateway que `DEPLOYMENT_INVARIANTS.md` torna obrigatório. Dizia
"~25x, até ~60x no pior caso".

Medido em `/v1/models/analyze` com o corpo HTTP real como denominador, um documento cujos
componentes trazem só os três campos obrigatórios — perfeitamente válido, e a forma típica do que
um importador gera — dá **254x**. Quem dimensionasse por 60x subdimensionava por mais de quatro.

A razão, porém, é a variável errada, e é isso que o documento passou a dizer: a resposta é função
do **número de componentes**, não dos bytes do pedido. Medido nas duas formas do mesmo documento
de 1 005 componentes: 10,4 KB de resposta por componente no esparso e 11,3 no rico — enquanto a
razão salta de 254x para 29x. O que muda é o denominador, não a resposta.

Este teste mede e compara com o publicado, para que a próxima mudança no motor que engorde a
resposta não deixe o número a mentir em silêncio.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_API_DOC = _ROOT / "docs" / "features" / "API.md"
for _pkg in ("core-schema", "threat-engine", "exporters", "industry-packs", "report-premium"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))
sys.path.insert(0, str(_ROOT / "apps" / "api"))

_COMPONENTS = 200


def _documented(pattern: str, label: str) -> float:
    match = re.search(pattern, _API_DOC.read_text(encoding="utf-8"))
    assert match, f"docs/features/API.md não declara {label} numa forma legível: {pattern}"
    return float(match.group(1).replace(",", "."))


def _measure(*, rich: bool) -> tuple[int, int]:
    """(bytes do pedido, bytes da resposta) para `_COMPONENTS` componentes."""
    import logging

    logging.disable(logging.CRITICAL)
    from fastapi.testclient import TestClient
    from otm_api.main import app

    if rich:
        components = [
            {
                "id": f"c{i}",
                "name": f"Componente de negocio numero {i}",
                "kind": "process",
                "description": "Servico aplicacional com responsabilidades de dominio. " * 4,
                "technology": "Python/FastAPI",
            }
            for i in range(_COMPONENTS)
        ]
    else:
        components = [{"id": f"c{i}", "name": "a", "kind": "process"} for i in range(_COMPONENTS)]

    body = json.dumps(
        {"document": {"model": {"schema_version": "1.1.0"}, "metadata": {"title": "t"}, "components": components}},
        separators=(",", ":"),
    ).encode()
    response = TestClient(app, raise_server_exceptions=False).post(
        "/v1/models/analyze", content=body, headers={"content-type": "application/json"}
    )
    assert response.status_code == 200, response.text[:200]
    return len(body), len(response.content)


def test_a_razao_no_pior_caso_nao_esta_subestimada() -> None:
    documented = _documented(r"pior caso medido \*{0,2}~?([0-9]+)x", "a razão de pior caso")
    request_bytes, response_bytes = _measure(rich=False)
    measured = response_bytes / request_bytes

    # Banda de 10%: a razão varia alguns por cento com o tamanho do documento, e o que este teste
    # guarda é a subestimação **material** — a que motivou esta correcção era de mais de quatro vezes.
    assert measured <= documented * 1.10, (
        f"medido {measured:.0f}x contra {documented:.0f}x publicados — quem dimensionar o gateway "
        "pelo número publicado subdimensiona"
    )


def test_os_kb_por_componente_publicados_batem_com_a_medicao() -> None:
    documented = _documented(r"~?([0-9]+(?:[.,][0-9]+)?) KB de resposta por componente", "os KB por componente")

    for rich in (False, True):
        _, response_bytes = _measure(rich=rich)
        measured = response_bytes / _COMPONENTS / 1024
        assert 0.75 * documented <= measured <= 1.35 * documented, (
            f"medidos {measured:.1f} KB/componente ({'rico' if rich else 'esparso'}) contra {documented:.1f} publicados"
        )


@pytest.mark.parametrize("rich", [False, True])
def test_a_resposta_depende_dos_componentes_e_nao_do_pedido(rich: bool) -> None:
    """A premissa da correcção: é o denominador que muda, não a resposta."""
    request_bytes, response_bytes = _measure(rich=rich)

    assert response_bytes > 0 and request_bytes > 0
    per_component_kb = response_bytes / _COMPONENTS / 1024
    assert 7.0 <= per_component_kb <= 15.0, f"{per_component_kb:.1f} KB/componente fora da banda medida"
