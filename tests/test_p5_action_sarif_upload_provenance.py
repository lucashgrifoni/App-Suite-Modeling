"""P5 — o SARIF publicado tem de ser o que esta execução produziu.

O passo `Upload SARIF` corria com
`if: always() && inputs.upload-sarif == 'true' && inputs.sarif-out != ''`, sem nunca referir
`steps.analyze`. O `always()` é deliberado e correcto — o comentário do passo seguinte di-lo por
extenso: quando o gate reprova, é exactamente essa a execução em que se quer o SARIF visível.

O que não é correcto é a outra metade do que `always()` abrange. Se `Analyze` falhar (ou se
`Set up Python`, `Install` ou `Validate` falharem antes dele), esta execução **não produziu SARIF
nenhum** — e o passo publicava na mesma o que estivesse em
`${inputs.working-directory}/${inputs.sarif-out}`, incluindo um ficheiro versionado no repositório
que está a ser analisado, rotulando-o como a análise desta execução.

Numa action que **outros** repositórios correm, isso é integridade de sinal: quem controla o
repositório analisado controla tanto o conteúdo desse ficheiro como a possibilidade de fazer a
análise falhar. Um SARIF limpo publicado sob a categoria da ferramenta fecha os alertas reais que
lá estavam, como "no longer detected".

A distinção que a correcção faz é entre **"o gate reprovou"** (a análise correu, há evidência
verdadeira, publique-se) e **"a análise não correu"** (não há nada desta execução para publicar).
`steps.analyze.outcome == 'success'` separa as duas sem tocar no `always()`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parents[1]


def _action() -> dict[str, Any]:
    return yaml.safe_load((_ROOT / "action.yml").read_text(encoding="utf-8"))


def _step(name: str) -> dict[str, Any]:
    for step in _action()["runs"]["steps"]:
        if step.get("name") == name:
            return step
    raise AssertionError(f"action.yml não tem um passo chamado {name!r}")


def _upload_condition() -> str:
    return str(_step("Upload SARIF")["if"])


def test_o_upload_exige_que_a_analise_tenha_corrido() -> None:
    """Sem isto, publica-se um ficheiro que esta execução não escreveu."""
    assert "steps.analyze" in _upload_condition(), (
        "a condição do upload não olha para o resultado da análise, "
        f"portanto publica o que estiver no caminho: {_upload_condition()!r}"
    )


def test_a_exigencia_e_sucesso_e_nao_apenas_ter_corrido() -> None:
    """`outcome` de uma análise falhada é `failure`; só `success` significa que há SARIF desta run."""
    condition = _upload_condition()

    assert "steps.analyze.outcome == 'success'" in condition


def test_o_upload_continua_a_acontecer_quando_o_gate_reprova() -> None:
    """Travão da intenção original: um gate reprovado é a execução em que mais se quer o SARIF.

    Se a correcção tivesse trocado `always()` por `success()`, um gate reprovado deixaria de
    publicar a evidência — teria comprado integridade ao preço de esconder achados verdadeiros.
    """
    condition = _upload_condition()

    assert "always()" in condition, "sem `always()` um gate reprovado deixa de publicar o SARIF"
    assert "steps.gate" not in condition, "o upload não pode depender do veredito do gate"


def test_a_analise_e_o_passo_que_escreve_o_ficheiro() -> None:
    """O teste acima só faz sentido se for mesmo `analyze` a produzir o SARIF."""
    analyze = _step("Analyze")

    assert analyze.get("id") == "analyze"
    assert "--sarif-out" in str(analyze["run"])
    assert "sarif-file=" in str(analyze["run"])


def test_as_condicoes_de_upload_que_ja_existiam_mantem_se() -> None:
    """A correcção acrescenta uma exigência; não pode remover as que já lá estavam."""
    condition = _upload_condition()

    assert "inputs.upload-sarif == 'true'" in condition
    assert "inputs.sarif-out != ''" in condition
