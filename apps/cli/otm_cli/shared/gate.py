"""Superfície de CLI do gate de risco: parsing de `--fail-on`, render e código de saída.

O veredito é calculado por `otm_threat_engine.gate.evaluate_gate` (função pura). Aqui só
traduzimos para a linha de comandos.

Contrato de códigos de saída (documentado no `--help`):
    0  sucesso, gate não reprovou (e sempre, quando nenhuma flag de gate é usada)
    1  erro de utilização (ficheiro inexistente, YAML inválido, `--fail-on` inválido)
    3  **gate reprovou** — há ameaças novas ou agravadas acima do limiar

`3` porque `1` já significa erro de utilização neste CLI e `2` já é usado por
`explain` (kind inválido); confundir "a política falhou" com "o comando falhou" é
precisamente o que um operador de CI não pode aceitar.

O relatório do gate vai para **stderr**, para sobreviver a `--format json > file.json`
e a pipes; o stdout mantém-se byte-a-byte igual ao de hoje.
"""

from __future__ import annotations

from otm_threat_engine import SEVERITY_ORDER, Severity
from otm_threat_engine.gate import GateResult

from otm_cli.shared.errors import CliUserError

#: Código de saída quando a política reprova (distinto de erro de utilização).
GATE_TRIP_EXIT_CODE = 3

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


def render_gate_result(result: GateResult) -> str:
    """Bloco legível em log de CI. Só chamado quando a política está activa."""
    policy = result.policy
    criteria: list[str] = []
    if policy.fail_on:
        criteria.append(f"--fail-on={policy.fail_on}")
    if policy.fail_on_risk_increase:
        criteria.append("--fail-on-risk-increase")
    header_policy = " ".join(criteria)

    bar = "=" * 60
    if result.not_evaluated_reason:
        status = "NOT EVALUATED"
    elif result.tripped:
        status = "FAILED"
    else:
        status = "PASSED"
    lines = [bar, f"THREAT MODEL GATE: {status}   policy: {header_policy}", bar]

    if result.not_evaluated_reason == "methodology_changed":
        # Deliberately not "PASSED": nothing was judged. Saying "passed" here would be the
        # gate claiming a clean bill of health it never checked.
        lines.append(
            "The methodology changed between the two models, so the heuristics differ and new or "
            "worsened threats cannot be attributed to the model change. No verdict was issued; "
            "exit code 0. Re-run the gate with both sides on the same methodology to get one."
        )
    elif not result.tripped:
        lines.append("No new or worsened threats at or above the threshold.")
    else:
        new = result.new_threats
        worsened = result.worsened_threats
        risk = [t for t in result.trips if t.kind == "risk_increase"]
        lines.append(f"{len(result.trips)} condition(s) hit. Exit code {GATE_TRIP_EXIT_CODE}.")

        if new:
            lines.append("")
            lines.append(f"NEW threats at/above {policy.fail_on} ({len(new)}):")
            for t in new:
                sev = (t.severity_after or "").upper()
                lines.append(f"  [{sev:<8} {_fmt(t.score_after):>5}]  {t.threat_id}")

        if worsened:
            lines.append("")
            lines.append(f"WORSENED threats crossing into {policy.fail_on}+ ({len(worsened)}):")
            for t in worsened:
                before = (t.severity_before or "").upper()
                after = (t.severity_after or "").upper()
                renamed = f"  (was `{t.paired_id}`)" if t.paired_id else ""
                lines.append(
                    f"  [{before} {_fmt(t.score_before)} -> {after} {_fmt(t.score_after)}]  {t.threat_id}{renamed}"
                )

        if risk:
            lines.append("")
            for t in risk:
                if t.threat_id is None:
                    lines.append(f"MAX RISK increased: {_fmt(t.score_before)} -> {_fmt(t.score_after)}")
                else:
                    renamed = f"  (was `{t.paired_id}`)" if t.paired_id else ""
                    lines.append(
                        f"RISK increased (within band): {_fmt(t.score_before)} -> "
                        f"{_fmt(t.score_after)}  {t.threat_id}{renamed}"
                    )

    if result.unranked_threat_ids:
        lines.append("")
        lines.append(
            f"Note: {len(result.unranked_threat_ids)} new threat(s) carry no score and were not "
            f"evaluated against the band: {', '.join(result.unranked_threat_ids)}"
        )

    lines.append(bar)
    return "\n".join(lines)
