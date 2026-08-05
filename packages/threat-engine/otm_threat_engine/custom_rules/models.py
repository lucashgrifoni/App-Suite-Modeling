"""Modelo declarativo das regras personalizadas de uma organização.

Contrato deliberadamente pequeno. Uma regra **descreve** o que procurar; não executa nada.
Não há expressões, código, `eval`, regex arbitrária nem import dinâmico — o pior que um
ficheiro de regras malicioso consegue fazer é descrever ameaças que não interessam a ninguém.

Uma regra tem exactamente **um** sujeito: componentes ou fluxos. Isso mantém óbvio quantas
ameaças ela emite (uma por alvo que casa) e evita semântica de junção que ninguém pediu.
Regras que cruzam entidades ficam para uma versão futura, aditivamente.
"""

from __future__ import annotations

import re
from typing import Annotated, Any, Literal

from otm_core_schema import Asset, Component, DataFlow, StrideCategory
from pydantic import BaseModel, ConfigDict, Field, model_validator

#: Ids entram em ids de ameaça gerados, em nomes de ficheiro de relatório e em tabelas
#: Markdown. Restringir a um slug ASCII evita ter de escapar em cada superfície de saída.
_ID_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,48}$"
RuleId = Annotated[str, Field(pattern=_ID_PATTERN)]

#: Campos de `DataFlow` que o motor deriva em vez de ler do documento.
DERIVED_FLOW_FIELDS: dict[str, type] = {"crosses_boundary": bool}

#: Campos que nunca fazem sentido como critério: identificadores e texto livre.
_UNMATCHABLE = {"id", "name", "description", "metadata"}


def _matchable_fields(model: type[BaseModel]) -> dict[str, Any]:
    return {name: info for name, info in model.model_fields.items() if name not in _UNMATCHABLE}


COMPONENT_MATCH_FIELDS = _matchable_fields(Component)
FLOW_MATCH_FIELDS = {**_matchable_fields(DataFlow), **DERIVED_FLOW_FIELDS}
ASSET_MATCH_FIELDS = _matchable_fields(Asset)


class _MatchBlock(BaseModel):
    """Critérios sobre um sujeito. Todas as chaves têm de casar (AND).

    Um escalar é igualdade; uma lista é "qualquer um destes" (OR). É a totalidade da
    linguagem, e é de propósito: um autor de regras consegue ler a regra dele em voz alta.
    """

    model_config = ConfigDict(extra="allow")

    def criteria(self) -> dict[str, Any]:
        return dict(self.__pydantic_extra__ or {})


class ComponentMatch(_MatchBlock):
    @model_validator(mode="after")
    def _known_fields_only(self) -> ComponentMatch:
        _reject_unknown(self.criteria(), COMPONENT_MATCH_FIELDS, "component")
        return self


class FlowMatch(_MatchBlock):
    @model_validator(mode="after")
    def _known_fields_only(self) -> FlowMatch:
        _reject_unknown(self.criteria(), FLOW_MATCH_FIELDS, "flow")
        return self


class AssetMatch(_MatchBlock):
    @model_validator(mode="after")
    def _known_fields_only(self) -> AssetMatch:
        _reject_unknown(self.criteria(), ASSET_MATCH_FIELDS, "asset")
        return self


def _reject_unknown(criteria: dict[str, Any], allowed: dict[str, Any], subject: str) -> None:
    """Um campo escrito com erro é o pior modo de falha possível aqui.

    Ignorá-lo em silêncio produz uma regra que nunca casa: a organização acredita que está
    coberta e não está. Falha ruidosa, com a lista de campos válidos.
    """
    unknown = sorted(set(criteria) - set(allowed))
    if not unknown:
        return
    known = ", ".join(sorted(allowed))
    raise ValueError(f"unknown {subject} field(s) {unknown}. Valid fields: {known}")


class RuleMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    component: ComponentMatch | None = None
    flow: FlowMatch | None = None
    asset: AssetMatch | None = None

    @model_validator(mode="after")
    def _exactly_one_subject(self) -> RuleMatch:
        chosen = [s for s in ("component", "flow", "asset") if getattr(self, s) is not None]
        if len(chosen) != 1:
            raise ValueError(
                "a rule matches exactly one subject: give `component:`, `flow:` or `asset:`, not "
                f"{'several' if len(chosen) > 1 else 'none'}."
            )
        block = self.component or self.flow or self.asset
        if block is not None and not block.criteria():
            raise ValueError("the match block is empty; a rule that matches everything is not a rule.")
        return self

    @property
    def subject(self) -> Literal["component", "flow", "asset"]:
        if self.component is not None:
            return "component"
        return "flow" if self.flow is not None else "asset"


class CustomRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: RuleId
    title: str = Field(min_length=1, max_length=200)
    stride: StrideCategory
    match: RuleMatch
    description: str | None = Field(default=None, max_length=2000)
    #: Somados a uma base de 3, e depois limitados a [1,5] — o mesmo cálculo dos industry packs.
    likelihood_delta: int = Field(default=0, ge=-2, le=2)
    impact_delta: int = Field(default=0, ge=-2, le=2)
    #: Referências livres (CWE-306, ASVS 4.0.3 V2.2.1, uma norma interna). São rótulos de
    #: rastreabilidade, não uma alegação de cobertura.
    refs: list[str] = Field(default_factory=list, max_length=20)
    control_hint: str | None = Field(default=None, max_length=500)


class CustomRuleSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: RuleId
    rules: list[CustomRule] = Field(min_length=1, max_length=500)
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _unique_rule_ids(self) -> CustomRuleSet:
        seen: set[str] = set()
        dupes = sorted({r.id for r in self.rules if r.id in seen or seen.add(r.id)})  # type: ignore[func-returns-value]
        if dupes:
            raise ValueError(f"duplicate rule id(s): {dupes}. Ids must be unique within a rule set.")
        return self


def is_valid_id(value: str) -> bool:
    return re.match(_ID_PATTERN, value) is not None
