"""P5 — o não-veredito do gate era anunciado como erro de utilização, e não escrevia `gate-outcome`.

O passo `Threat-model drift gate` distinguia "aprovado" de "não avaliado" procurando `NOT EVALUATED`
no relatório — mas fazia-o dentro do ramo `case 0)`, e o CLI **nunca** sai com 0 nesse estado:
`apps/cli/otm_cli/shared/gate.py:44` define `GATE_NOT_EVALUATED_EXIT_CODE = 1` e a linha 198
devolve-o sempre que há `not_evaluated_reason`. Aquele `grep` era portanto código morto, e o caso
real caía no ramo `*)`, que o anuncia como *"usage or input error, not a gate verdict"* e não
escreve valor nenhum em `GITHUB_OUTPUT`.

Três consequências, todas em superfície que **outros** repositórios consomem:

1. `gate-outcome: not-evaluated` — documentado em `action.yml` e no README — era inalcançável a
   partir do CLI. Quem ramifique nesse valor nunca o vê.
2. Um não-veredito legítimo (mudança de metodologia entre os dois modelos) era descrito ao
   utilizador como erro seu.
3. `gate-outcome` ficava vazio, portanto "o gate recusou-se a julgar" e "a invocação estava
   errada" tornavam-se indistinguíveis — que é exactamente a distinção que o output existe para
   fazer.

O marcador é estável e vem do produto: `gate.py:_status_label` devolve o literal `NOT EVALUATED`
sempre que `not_evaluated_reason` está preenchido, e esse texto entra no relatório.

**O que este ficheiro NÃO prova.** É uma asserção *estrutural* sobre o shell do passo, não uma
execução dele. Executá-lo exigiria um runner do GitHub Actions. O que se garante aqui é que a
classificação não volta a ficar presa a um código de saída que o produto não emite, e que nenhum
caminho não-zero deixa `gate-outcome` por escrever.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parents[1]


def _gate_script() -> str:
    action: dict[str, Any] = yaml.safe_load((_ROOT / "action.yml").read_text(encoding="utf-8"))
    for step in action["runs"]["steps"]:
        if step.get("id") == "gate" or "drift gate" in str(step.get("name", "")).lower():
            return str(step["run"])
    raise AssertionError("action.yml não tem o passo do gate")


def _case_body(script: str) -> str:
    """O bloco `case ... esac` que classifica o código de saída do CLI."""
    start = script.index('case "${rc}" in')
    return script[start : script.index("esac", start)]


def test_a_classificacao_nao_depende_de_um_codigo_de_saida_que_o_cli_nao_emite() -> None:
    """`NOT EVALUATED` chega com saída 1, nunca com 0; procurá-lo só no ramo `0)` é código morto.

    A asserção tem de ser sobre a inspecção **do relatório do CLI**, não sobre a string em geral:
    o script já a contém no caminho em que a baseline não se consegue ler, que é outro assunto. A
    primeira versão deste teste passava por causa dessa ocorrência — passava pelo motivo errado,
    que é a única coisa pior do que falhar.

    A invariante é **o ramo ser alcançável**, e não a verificação vir antes do `case`. A primeira
    versão exigia o segundo, que é uma das formas de garantir o primeiro e não a única: pô-la no
    ramo `*)`, onde a saída 1 aterra, satisfaz a invariante e fecha um buraco que estar antes do
    `case` abria — o relatório cita o título do modelo, e antes do `case` esse título conseguia
    reclassificar um gate reprovado. Ver `tests/test_p4_gate_verdict_is_not_model_controlled.py`.
    """
    script = _gate_script()
    body = _case_body(script)
    fallback_arm = body[body.index("*)") :]

    assert script.count('"${report}"'), "o relatório do CLI tem de ser inspeccionado em algum lado"
    assert "NOT EVALUATED" in fallback_arm, (
        "a deteção do não-veredito tem de viver onde a saída 1 aterra; noutro ramo é código morto"
    )


def test_o_ramo_de_saida_zero_nao_reclama_o_nao_veredito() -> None:
    """Depois de detectado antes, o ramo `0)` só pode significar aprovação."""
    body = _case_body(_gate_script())
    zero_arm = body[body.index("0)") : body.index("3)")]

    assert "NOT EVALUATED" not in zero_arm


def test_todo_o_caminho_nao_zero_escreve_um_gate_outcome() -> None:
    """Um `gate-outcome` vazio faz "recusei julgar" e "chamaste-me mal" indistinguíveis."""
    body = _case_body(_gate_script())
    fallback = body[body.index("*)") :]

    assert "outcome=" in fallback, "o ramo de erro não escreve `gate-outcome`"


def test_o_nao_veredito_continua_a_falhar_o_passo() -> None:
    """Não pode virar um check verde: um gate que não julgou nada não diz `no new risk`.

    Este é o travão que impede a correcção de comprar clareza com permissividade.
    """
    script = _gate_script()

    assert "exit 1" in script or 'exit "${rc}"' in script


def test_o_valor_documentado_existe_no_contrato_da_action() -> None:
    action = yaml.safe_load((_ROOT / "action.yml").read_text(encoding="utf-8"))

    assert "not-evaluated" in action["outputs"]["gate-outcome"]["description"]


def test_o_codigo_de_saida_do_nao_veredito_continua_a_ser_o_que_o_teste_assume() -> None:
    """Se o produto mudar este número, a correcção acima passa a estar errada — falhe aqui.

    O teste não deve depender de uma constante que possa mover-se em silêncio noutro pacote.
    """
    gate = (_ROOT / "apps" / "cli" / "otm_cli" / "shared" / "gate.py").read_text(encoding="utf-8")

    assert "GATE_NOT_EVALUATED_EXIT_CODE = 1" in gate
