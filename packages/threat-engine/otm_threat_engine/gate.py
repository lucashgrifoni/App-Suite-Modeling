"""Gate de risco sobre um `AnalysisDiff` — o análogo de threat modeling a um security gate de CI.

Função pura: recebe o diff entre duas análises e uma política, devolve o veredito.
Não conhece CLI, ficheiros nem códigos de saída.

Princípios (nesta ordem):

1. **Nunca reprovar por algo que o programador não causou.** Só disparam ameaças *novas* ou
   *agravadas*. Remoções, melhorias, descidas de score e troca de metodologia nunca disparam.
   Não disparar não é o mesmo que aprovar: a troca de metodologia sai daqui como
   `not_evaluated`, e quem traduz o veredito em código de saída fecha o gate na mesma
   (`otm_cli.shared.gate.gate_exit_code`) — só o `0` diz "sem risco novo".

2. **Nunca aprovar em silêncio o que devia disparar.** Uma ameaça cujo id mudou aparece como um
   par `(added, removed)` — nunca em `modified` — e a assinatura de remapeamento **ignora o score**.
   Tratar todo o remapeamento como inerte deixaria passar uma ameaça que mudou de id *e* subiu de
   `medium` para `critical`. Por isso um par remapeado é avaliado como ameaça **agravada**,
   comparando o score do gémeo removido.

3. **Nada é descartado sem registo.** Ameaças novas sem score são reportadas como `unranked`,
   nunca ignoradas em silêncio.

A banda vem de `severity_for_score` (fonte única), a mesma que alimenta
`summary.severity_distribution` e os níveis SARIF.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from otm_threat_engine.comparison_models import AnalysisDiff, HeuristicThreatDelta
from otm_threat_engine.severity import Severity, severity_at_least, severity_for_score, severity_rank

TripKind = Literal["new_threat", "worsened_threat", "risk_increase"]
NotEvaluatedReason = Literal["methodology_changed"]


class GatePolicy(BaseModel):
    """O que faz o gate reprovar. Tudo desligado por omissão."""

    fail_on: Severity | None = Field(
        default=None,
        description="Banda mínima (inclusive) que reprova. `None` desliga o critério de banda.",
    )
    fail_on_risk_increase: bool = Field(
        default=False,
        description="Reprova quando o score máximo sobe, mesmo sem mudança de banda.",
    )

    @property
    def active(self) -> bool:
        return self.fail_on is not None or self.fail_on_risk_increase


class GateTrip(BaseModel):
    """Uma razão concreta para reprovar."""

    kind: TripKind
    threat_id: str | None = None
    paired_id: str | None = Field(default=None, description="Id anterior, quando a ameaça mudou de id.")
    score_before: float | None = None
    score_after: float | None = None
    severity_before: Severity | None = None
    severity_after: Severity | None = None


class GateResult(BaseModel):
    """Veredito do gate. `tripped` é a única coisa que decide o exit code."""

    tripped: bool = False
    policy: GatePolicy
    trips: list[GateTrip] = Field(default_factory=list)
    unranked_threat_ids: list[str] = Field(
        default_factory=list,
        description="Ameaças novas sem score: não avaliáveis por banda, reportadas em vez de ignoradas.",
    )
    not_evaluated_reason: NotEvaluatedReason | None = Field(
        default=None,
        description=(
            "Preenchido quando a política estava activa mas o diff não é atribuível à mudança do "
            "modelo. Não é um PASSED: é um 'não avaliado', e tem de ser dito em voz alta."
        ),
    )

    @property
    def new_threats(self) -> list[GateTrip]:
        return [t for t in self.trips if t.kind == "new_threat"]

    @property
    def worsened_threats(self) -> list[GateTrip]:
        return [t for t in self.trips if t.kind == "worsened_threat"]


def _is_remap(h: HeuristicThreatDelta) -> bool:
    # A remap with no baseline score cannot be compared, so it is treated as genuinely new
    # (fail-closed) rather than silently skipped.
    return h.match_kind == "signature_remap" and h.score_before is not None


def _new_threat_trips(added: list[HeuristicThreatDelta], threshold: Severity) -> tuple[list[GateTrip], list[str]]:
    trips: list[GateTrip] = []
    unranked: list[str] = []
    for h in added:
        if _is_remap(h):
            continue  # evaluated as a worsening candidate instead
        if h.score_after is None:
            unranked.append(h.threat_id)
            continue
        band = severity_for_score(h.score_after)
        if severity_at_least(band, threshold):
            trips.append(
                GateTrip(
                    kind="new_threat",
                    threat_id=h.threat_id,
                    score_after=h.score_after,
                    severity_after=band,
                )
            )
    return trips, unranked


def _worsened_trips(diff: AnalysisDiff, threshold: Severity) -> list[GateTrip]:
    # Both id-matched `modified` threats and remapped `added` threats can have worsened.
    candidates = [*diff.heuristic_threats.modified, *(h for h in diff.heuristic_threats.added if _is_remap(h))]
    trips: list[GateTrip] = []
    for h in candidates:
        if h.score_before is None or h.score_after is None or h.score_after <= h.score_before:
            continue
        before = severity_for_score(h.score_before)
        after = severity_for_score(h.score_after)
        # Only a band CROSSING trips here: a within-band bump (21 -> 22) is not a *severity*
        # regression. `--fail-on-risk-increase` is what covers within-band worsening — and it
        # does so per threat, not only on the summary maximum (see `_risk_increase_trips`).
        if severity_at_least(after, threshold) and severity_rank(after) > severity_rank(before):
            trips.append(
                GateTrip(
                    kind="worsened_threat",
                    threat_id=h.threat_id,
                    paired_id=h.paired_id,
                    score_before=h.score_before,
                    score_after=h.score_after,
                    severity_before=before,
                    severity_after=after,
                )
            )
    return trips


def _risk_increase_trips(diff: AnalysisDiff, *, exclude_ids: set[str]) -> list[GateTrip]:
    """Subidas de score que a banda não apanha.

    O critério de banda só dispara ao *atravessar* uma banda. Sem isto, uma ameaça que sobe
    `12 -> 15` (ambos `high`) não é apanhada por política nenhuma, porque `max_risk_delta` é o
    máximo do *resumo*: se a ameaça agravada não for a de score máximo, o delta global é `0`.
    Era um fail-open silencioso na política mais estrita que o CLI oferece.

    Reporta o máximo do resumo **e** cada ameaça cujo score subiu, excluindo as que já foram
    reportadas como `worsened_threat` para não duplicar a mesma ameaça no relatório.
    """
    trips: list[GateTrip] = []

    if diff.max_risk_delta is not None and diff.max_risk_delta > 0:
        trips.append(
            GateTrip(
                kind="risk_increase",
                score_before=diff.max_risk_before,
                score_after=diff.max_risk_after,
            )
        )

    candidates = [*diff.heuristic_threats.modified, *(h for h in diff.heuristic_threats.added if _is_remap(h))]
    for h in candidates:
        if h.threat_id in exclude_ids:
            continue
        if h.score_before is None or h.score_after is None or h.score_after <= h.score_before:
            continue
        trips.append(
            GateTrip(
                kind="risk_increase",
                threat_id=h.threat_id,
                paired_id=h.paired_id,
                score_before=h.score_before,
                score_after=h.score_after,
                severity_before=severity_for_score(h.score_before),
                severity_after=severity_for_score(h.score_after),
            )
        )
    return trips


def evaluate_gate(diff: AnalysisDiff, policy: GatePolicy) -> GateResult:
    """Aplica a política ao diff. Sem política activa, nunca reprova."""
    if not policy.active:
        return GateResult(tripped=False, policy=policy)

    # Princípio 1: nunca reprovar por algo que o programador não causou. Trocar de metodologia
    # troca a própria régua — as heurísticas de uma lente não existem na outra, por isso as
    # ameaças "novas" não são atribuíveis à mudança do modelo. O comando irmão já recusa
    # comparar entre versões do motor pela mesma razão; aqui o diff continua a ser produzido,
    # mas o gate não emite veredito. Não é PASSED, é `not_evaluated` — e é dito em voz alta.
    #
    # `tripped=False` diz só "a política não foi violada", nunca "o modelo está limpo": a
    # metodologia declara-se dentro do modelo em revisão, portanto quem abre o PR controla esta
    # condição. Quem transforma o veredito em código de saída trata `not_evaluated` como
    # não-zero, senão bastava uma linha no ficheiro sob revisão para desligar o gate.
    if diff.methodology_changed:
        return GateResult(tripped=False, policy=policy, not_evaluated_reason="methodology_changed")

    trips: list[GateTrip] = []
    unranked: list[str] = []

    if policy.fail_on is not None:
        new_trips, unranked = _new_threat_trips(diff.heuristic_threats.added, policy.fail_on)
        trips.extend(new_trips)
        trips.extend(_worsened_trips(diff, policy.fail_on))

    if policy.fail_on_risk_increase:
        already = {t.threat_id for t in trips if t.threat_id is not None}
        trips.extend(_risk_increase_trips(diff, exclude_ids=already))

    return GateResult(tripped=bool(trips), policy=policy, trips=trips, unranked_threat_ids=unranked)
