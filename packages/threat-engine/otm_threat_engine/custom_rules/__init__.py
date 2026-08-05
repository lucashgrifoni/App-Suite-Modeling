"""Regras de ameaça declaradas por quem adopta a ferramenta.

Permite acrescentar heurísticas específicas da organização sem forkar o motor. As regras são
dados, não código: descrevem o que procurar num modelo e que ameaça emitir quando encontram.
"""

from otm_threat_engine.custom_rules.loader import MAX_RULES_FILE_BYTES, load_custom_rules
from otm_threat_engine.custom_rules.models import (
    COMPONENT_MATCH_FIELDS,
    FLOW_MATCH_FIELDS,
    ComponentMatch,
    CustomRule,
    CustomRuleSet,
    FlowMatch,
    RuleMatch,
)
from otm_threat_engine.custom_rules.runtime import (
    ID_PREFIX,
    collect_control_hints,
    iter_custom_rule_threats,
)

__all__ = [
    "COMPONENT_MATCH_FIELDS",
    "FLOW_MATCH_FIELDS",
    "ID_PREFIX",
    "MAX_RULES_FILE_BYTES",
    "ComponentMatch",
    "CustomRule",
    "CustomRuleSet",
    "FlowMatch",
    "RuleMatch",
    "collect_control_hints",
    "iter_custom_rule_threats",
    "load_custom_rules",
]
