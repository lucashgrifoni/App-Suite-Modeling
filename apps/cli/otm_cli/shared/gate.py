"""Superfície de CLI do gate de risco: parsing de `--fail-on`, render e código de saída.

O veredito é calculado por `otm_threat_engine.gate.evaluate_gate` (função pura). Aqui só
traduzimos para a linha de comandos.

Contrato de códigos de saída:
    0  sucesso, gate não reprovou (e sempre, quando nenhuma flag de gate é usada)
    1  erro de utilização levantado pelo CLI: ficheiro inexistente, YAML inválido,
       `--fail-on` inválido, pack desconhecido, destino de escrita inacessível — **e** um
       gate armado que não conseguiu emitir veredito (ver `gate_exit_code`)
    2  erro de utilização levantado pelo Typer/Click: valor inválido num enum
       (`--methodology`, `--format`, `--kind`), flag desconhecida, argumento em falta
    3  **gate reprovou** — há ameaças novas ou agravadas acima do limiar

Um script de CI que queira distinguir "o comando estava mal escrito" de "a política
falhou" tem de tratar **1 e 2** como erro de utilização. `2` não é exclusivo do
`explain`: é a convenção do Click para qualquer erro de parsing, e este CLI não a
sobrepõe. `3` fica reservado para a política precisamente porque `1` e `2` já estão
tomados — confundir "a política falhou" com "o comando falhou" é o que um operador
de CI não pode aceitar.

O relatório do gate vai para **stderr**, para sobreviver a `--format json > file.json`
e a pipes; o stdout mantém-se byte-a-byte igual ao de hoje.
"""

from __future__ import annotations

from otm_threat_engine import SEVERITY_ORDER, Severity
from otm_threat_engine.gate import GatePolicy, GateResult, GateTrip

from otm_cli.shared.errors import CliUserError

#: Código de saída quando a política reprova (distinto de erro de utilização).
GATE_TRIP_EXIT_CODE = 3

#: Código de saída quando um gate **armado** não conseguiu emitir veredito.
#:
#: É o mesmo `1` com que `otm diff-analysis` já recusa comparar duas análises de versões
#: diferentes do motor ou de packs diferentes: o comando, tal como foi escrito, não consegue
#: produzir um veredito. Sair `0` aqui seria um fail-open — e num gate de CI o `0` é lido como
#: build verde, por quem o escreveu e pela action que o embrulha.
GATE_NOT_EVALUATED_EXIT_CODE = 1

_NONE = "none"
_ALLOWED = (_NONE, *SEVERITY_ORDER)


def parse_fail_on(value: str | None) -> Severity | None:
    """`none`/vazio → `None` (critério desligado). Valor inválido → erro de utilização (exit 1)."""
    if value is None:
        return None
    normalized = value.strip().lower()
    if normalized in ("", _NONE):
        return None
    if normalized not in SEVERITY_ORDER:
        raise CliUserError(
            exit_code=1,
            failed=f"invalid `--fail-on` value `{value}`.",
            cause=f"must be one of: {', '.join(_ALLOWED)}.",
            next_step="pick a severity threshold; the gate trips at that band or above.",
        )
    return normalized


def _fmt(score: float | None) -> str:
    return "—" if score is None else f"{score:g}"


_BAR = "=" * 60

#: Deliberately not "PASSED": nothing was judged. Saying "passed" here would be the gate
#: claiming a clean bill of health it never checked — and exiting 0 would say exactly that to
#: every CI runner, which is why an armed gate that reaches this state exits non-zero.
_NOT_EVALUATED_NOTE = (
    "The methodology changed between the two models, so the heuristics differ and new or "
    f"worsened threats cannot be attributed to the model change. No verdict was issued; exit "
    f"code {GATE_NOT_EVALUATED_EXIT_CODE}, because a gate that judged nothing must not answer "
    "the code that means `no new risk`. Pin one lens with `--methodology`/`-m` on both sides "
    "to get a verdict."
)


def _status_label(result: GateResult) -> str:
    """`NOT EVALUATED` tem precedência: um não-veredito nunca se lê como aprovação."""
    if result.not_evaluated_reason:
        return "NOT EVALUATED"
    return "FAILED" if result.tripped else "PASSED"


def _policy_summary(policy: GatePolicy) -> str:
    """As flags que armaram o gate, tal como foram escritas na linha de comandos."""
    criteria: list[str] = []
    if policy.fail_on:
        criteria.append(f"--fail-on={policy.fail_on}")
    if policy.fail_on_risk_increase:
        criteria.append("--fail-on-risk-increase")
    return " ".join(criteria)


def _renamed_suffix(trip: GateTrip) -> str:
    """`(was ...)` só quando a ameaça mudou de id — senão o leitor procura um id que não existe."""
    return f"  (was `{trip.paired_id}`)" if trip.paired_id else ""


def _new_threat_lines(trips: list[GateTrip], threshold: Severity | None) -> list[str]:
    """Empty in, empty out: each section owns the rule that it disappears when it has nothing
    to say, so no caller can leave a bare `NEW threats` header over an empty list."""
    if not trips:
        return []
    lines = ["", f"NEW threats at/above {threshold} ({len(trips)}):"]
    for t in trips:
        sev = (t.severity_after or "").upper()
        lines.append(f"  [{sev:<8} {_fmt(t.score_after):>5}]  {t.threat_id}")
    return lines


def _worsened_threat_lines(trips: list[GateTrip], threshold: Severity | None) -> list[str]:
    if not trips:
        return []
    lines = ["", f"WORSENED threats crossing into {threshold}+ ({len(trips)}):"]
    for t in trips:
        before = (t.severity_before or "").upper()
        after = (t.severity_after or "").upper()
        lines.append(
            f"  [{before} {_fmt(t.score_before)} -> {after} {_fmt(t.score_after)}]  {t.threat_id}{_renamed_suffix(t)}"
        )
    return lines


def _risk_increase_lines(trips: list[GateTrip]) -> list[str]:
    """Subidas de score. Sem `threat_id` é o máximo do resumo, não uma ameaça concreta."""
    if not trips:
        return []
    lines = [""]
    for t in trips:
        if t.threat_id is None:
            lines.append(f"MAX RISK increased: {_fmt(t.score_before)} -> {_fmt(t.score_after)}")
        else:
            lines.append(
                f"RISK increased (within band): {_fmt(t.score_before)} -> "
                f"{_fmt(t.score_after)}  {t.threat_id}{_renamed_suffix(t)}"
            )
    return lines


def _verdict_lines(result: GateResult) -> list[str]:
    """O corpo do relatório: não-avaliado, aprovado, ou a lista do que reprovou.

    Cada secção só aparece quando tem conteúdo — o cabeçalho de uma secção vazia diria ao
    leitor que houve ameaças novas onde não houve.
    """
    if result.not_evaluated_reason == "methodology_changed":
        return [_NOT_EVALUATED_NOTE]
    if not result.tripped:
        return ["No new or worsened threats at or above the threshold."]

    threshold = result.policy.fail_on
    return [
        f"{len(result.trips)} condition(s) hit. Exit code {GATE_TRIP_EXIT_CODE}.",
        *_new_threat_lines(result.new_threats, threshold),
        *_worsened_threat_lines(result.worsened_threats, threshold),
        *_risk_increase_lines([t for t in result.trips if t.kind == "risk_increase"]),
    ]


def _unranked_note_lines(unranked_threat_ids: list[str]) -> list[str]:
    """Princípio 3: nada é descartado sem registo."""
    if not unranked_threat_ids:
        return []
    return [
        "",
        f"Note: {len(unranked_threat_ids)} new threat(s) carry no score and were not "
        f"evaluated against the band: {', '.join(unranked_threat_ids)}",
    ]


def gate_exit_code(result: GateResult) -> int:
    """O código de saída que o veredito implica. Só chamado com a política activa.

    Três estados, três códigos — e o `0` é o único que um runner de CI lê como "sem risco novo",
    por isso é o único que um gate que **avaliou** pode devolver:

    * reprovou            → `3`, a política falhou;
    * não conseguiu avaliar → `1`, o comando como foi escrito não produz veredito;
    * aprovou             → `0`.

    O caso do meio era `0`. Bastava acrescentar `methodology: linddun` ao modelo em revisão —
    uma linha dentro do próprio artefacto a ser revisto — para um veredito FAILED passar a build
    verde, sem tocar no workflow. As duas condições irmãs em `diff-analysis` (versão do motor,
    pack) já falham fechadas com `1` pela mesma razão: quando as heurísticas dos dois lados não
    são as mesmas, o delta não é atribuível à mudança do modelo. Fecha-se aqui também, em vez de
    fixar uma lente à revelia, porque escolher a lente é uma decisão do operador — e a mensagem
    diz-lhe qual flag a fixa.
    """
    if result.not_evaluated_reason:
        return GATE_NOT_EVALUATED_EXIT_CODE
    return GATE_TRIP_EXIT_CODE if result.tripped else 0


def render_gate_result(result: GateResult) -> str:
    """Bloco legível em log de CI. Só chamado quando a política está activa."""
    return "\n".join(
        [
            _BAR,
            f"THREAT MODEL GATE: {_status_label(result)}   policy: {_policy_summary(result.policy)}",
            _BAR,
            *_verdict_lines(result),
            *_unranked_note_lines(result.unranked_threat_ids),
            _BAR,
        ]
    )
