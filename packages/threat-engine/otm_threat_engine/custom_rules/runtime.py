"""Aplicação das regras personalizadas ao documento.

Casa cada regra contra o sujeito que ela declara e emite uma `HeuristicThreat` por alvo.
Segue as mesmas convenções dos industry packs: id de ameaça namespaced, deduplicação contra
o que já foi coberto, e L×I derivado de deltas sobre a base 3.
"""

from __future__ import annotations

from typing import Any

from otm_core_schema import ThreatModelDocument
from otm_core_schema.document import FrameworkRef

from otm_threat_engine.custom_rules.models import CustomRule, CustomRuleSet
from otm_threat_engine.engine_support import cross_boundary_flow_ids
from otm_threat_engine.result import HeuristicThreat
from otm_threat_engine.risk_calc import build_risk_assessment

#: Prefixo dos ids gerados. Distingue à vista uma ameaça de regra da organização das
#: heurísticas do motor e das ameaças de industry pack.
ID_PREFIX = "custom"

#: Catálogo das referências declaradas numa regra. Deliberadamente separado dos catálogos
#: reais (capec, cwe, owasp_llm, ...): estas são etiquetas da organização, não uma alegação
#: de conformidade verificada.
CUSTOM_REF_FRAMEWORK = "custom"


def _clamp_li(value: int) -> int:
    return min(5, max(1, value))


def _normalize(value: Any) -> Any:
    """Enums comparam-se pelo valor, para a regra poder escrever `kind: datastore`."""
    return value.value if hasattr(value, "value") else value


def _criterion_matches(actual: Any, expected: Any) -> bool:
    actual = _normalize(actual)
    if isinstance(expected, list):
        return any(actual == _normalize(item) for item in expected)
    return bool(actual == _normalize(expected))


def _subject_matches(subject: Any, criteria: dict[str, Any], derived: dict[str, Any]) -> bool:
    for field, expected in criteria.items():
        actual = derived[field] if field in derived else getattr(subject, field, None)
        if not _criterion_matches(actual, expected):
            return False
    return True


def _build_threat(
    *,
    rule: CustomRule,
    ruleset: CustomRuleSet,
    target_id: str,
    is_flow: bool,
    skipped_as_duplicate: bool,
) -> HeuristicThreat:
    likelihood = _clamp_li(3 + rule.likelihood_delta)
    impact = _clamp_li(3 + rule.impact_delta)
    description = rule.description or (
        f"Organisation rule `{rule.id}` from rule set `{ruleset.id}`. "
        "Review against the control expected by the rule author."
    )
    return HeuristicThreat(
        id=f"{ID_PREFIX}_{ruleset.id}_{rule.id}_{target_id}",
        title=f"[rules:{ruleset.id}] {rule.title}",
        description=description,
        stride=rule.stride,
        target_component_id=None if is_flow else target_id,
        target_data_flow_id=target_id if is_flow else None,
        risk=build_risk_assessment(likelihood, impact),
        skipped_as_duplicate=skipped_as_duplicate,
        # `framework="custom"` mantém honesto o agregado por catálogo: estas referências
        # foram escritas por quem adoptou a ferramenta e não foram verificadas contra
        # nenhum standard. Não se misturam com as refs CAPEC/CWE que o motor produz.
        framework_refs=[
            FrameworkRef(framework=CUSTOM_REF_FRAMEWORK, control_id=ref, notes=f"declared by rule `{rule.id}`")
            for ref in rule.refs
        ],
    )


def iter_custom_rule_threats(
    doc: ThreatModelDocument,
    ruleset: CustomRuleSet,
) -> tuple[list[HeuristicThreat], set[str]]:
    """Ameaças geradas pelas regras da organização, por ordem determinística.

    **Não são suprimidas pela cobertura das heurísticas base**, ao contrário das ameaças de
    industry pack. É uma escolha deliberada: uma regra da organização diz algo mais
    específico do que a categoria STRIDE genérica ("todo o datastore precisa de cifra
    aprovada pela ACME", com o controlo, o dono e a referência interna). Marcá-la como
    duplicada de um "information disclosure" genérico apagava exactamente a informação pela
    qual alguém se deu ao trabalho de escrever a regra.

    A deduplicação existe só dentro do conjunto: a mesma regra nunca dispara duas vezes no
    mesmo alvo. Regras distintas no mesmo alvo são achados distintos, e devem sê-lo.

    Devolve também os ids das regras que **realmente** dispararam, para que só os controlos
    dessas apareçam no relatório.
    """
    out: list[HeuristicThreat] = []
    emitted: set[tuple[str, str]] = set()
    fired: set[str] = set()
    cross_flows = cross_boundary_flow_ids(doc)

    for rule in ruleset.rules:
        is_flow = rule.match.subject == "flow"
        block = rule.match.flow if is_flow else rule.match.component
        criteria = block.criteria() if block else {}
        subjects: list[Any] = list(doc.data_flows if is_flow else doc.components)

        for subject in subjects:
            derived = {"crosses_boundary": subject.id in cross_flows} if is_flow else {}
            if not _subject_matches(subject, criteria, derived):
                continue
            if (rule.id, subject.id) in emitted:
                continue
            emitted.add((rule.id, subject.id))
            fired.add(rule.id)
            out.append(
                _build_threat(
                    rule=rule,
                    ruleset=ruleset,
                    target_id=subject.id,
                    is_flow=is_flow,
                    skipped_as_duplicate=False,
                )
            )

    return out, fired


def collect_control_hints(ruleset: CustomRuleSet, fired_rule_ids: set[str]) -> list[str]:
    """Controlos das regras que dispararam, deduplicados e por ordem estável.

    Só das que dispararam: sugerir um controlo para uma ameaça que nunca foi levantada
    diz ao leitor que há um problema onde o motor não encontrou nenhum.
    """
    hints = [r.control_hint for r in ruleset.rules if r.control_hint and r.id in fired_rule_ids]
    return list(dict.fromkeys(hints))
