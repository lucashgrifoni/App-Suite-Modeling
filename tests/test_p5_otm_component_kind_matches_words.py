"""O tipo OTM de um componente é classificado por palavra, não por subcadeia.

`_kind_from_otm_type` procura cada palavra-chave com `in`. Cinco delas são fragmentos de palavras
comuns, e o importador tipifica mal o componente sem avisar ninguém:

    business-logic          -> queue            (`bus` dentro de "business")
    abuse-monitor           -> queue            (`bus` dentro de "abuse")
    sandbox                 -> datastore        (`db` dentro de "sandbox")
    risk-factor             -> user             (`actor` dentro de "factor")
    personalization-engine  -> user             (`person` dentro de "personalization")
    automobile-ecu          -> external_entity  (`mobile` dentro de "automobile")

O custo não é cosmético: o tipo escolhe as heurísticas. Um modelo cujos três componentes importam
como `queue`/`queue`/`datastore` em vez de `process` rende 11 ameaças em vez de 17 — as seis que
faltam são `spoofing` e `elevation_of_privilege` de cada um deles. O importador silencia ameaças
ao ler um nome.

O modo é uma decisão **por palavra**, e cada uma aqui tem a sua razão:

- `bus` por token — "business" tem-no no início, portanto só a fronteira à direita o rejeita;
- `db`, `actor`, `mobile` por radical — em "sandbox", "factor" e "automobile" a palavra-chave está
  precedida de letra, e a fronteira à esquerda chega; assim `dbms` e `actors` continuam a contar;
- `person` por token, porque "personalization" começa mesmo em fronteira; `persons` fica na lista
  para o plural não se perder;
- `waf` e `cdn` por token por serem siglas de três letras — sem colisão medida, mas é o modo que
  a sigla pede e nenhum tipo real se perde.

As restantes ficam de propósito por subcadeia. `type` é uma string livre e as formas concatenadas
são correntes — "apigateway", "memcached", "objectstorage", "jobqueue", "superuser" —
e em nenhuma delas a palavra-chave está em fronteira. Apertar palavras inteiras que não colidem
custava esses casos sem resolver nada; estão todos na tabela abaixo.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "artifact-import", "industry-packs", "framework-mappings"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

#: tipo OTM -> o `ComponentKind` que ele deve produzir.
_COLLISIONS = {
    "business-logic": "process",
    "business-service": "process",
    "abuse-monitor": "process",
    "sandbox": "process",
    "sandboxed-runner": "process",
    "risk-factor": "process",
    "form-factor": "process",
    "personalization-engine": "process",
    "automobile-ecu": "process",
}

_MUST_STILL_MATCH = {
    "message-bus": "queue",
    "event-bus": "queue",
    "service-bus": "queue",
    "job-queue": "queue",
    "kafka-topic": "queue",
    "db": "datastore",
    "postgres-db": "datastore",
    "dbms": "datastore",
    "object-storage": "datastore",
    "s3-bucket": "datastore",
    "actor": "user",
    "actors": "user",
    "person": "user",
    "persons": "user",
    "end-user": "user",
    "mobile": "external_entity",
    "mobile-app": "external_entity",
    "thin-client": "external_entity",
    "waf": "gateway",
    "aws-waf": "gateway",
    "cdn-edge": "gateway",
    "api-gateway": "gateway",
    "reverse-proxy": "gateway",
    # Formas concatenadas: a palavra-chave não está em fronteira nenhuma, e é por isso que as
    # palavras inteiras que não colidem continuam a ser procuradas por subcadeia.
    "apigateway": "gateway",
    "memcached": "datastore",
    "objectstorage": "datastore",
    "jobqueue": "queue",
    "superuser": "user",
    "messagebroker": "queue",
}


def _kind(otm_type: str) -> str:
    from otm_artifact_import.otm_native import _kind_from_otm_type

    return _kind_from_otm_type(otm_type).value


def test_uma_palavra_dentro_de_outra_nao_tipifica_o_componente() -> None:
    wrong = {t: _kind(t) for t, expected in _COLLISIONS.items() if _kind(t) != expected}

    assert not wrong, f"tipos classificados por subcadeia: {wrong}"


def test_os_tipos_que_a_lista_existe_para_apanhar_continuam_a_ser_apanhados() -> None:
    """O outro sentido: apertar o matching não pode calar os casos legítimos."""
    lost = {t: _kind(t) for t, expected in _MUST_STILL_MATCH.items() if _kind(t) != expected}

    assert not lost, f"tipos que deixaram de ser reconhecidos: {lost}"


def test_o_tipo_exacto_continua_a_ter_precedencia() -> None:
    """Round-trip das nossas próprias exportações OTM: o valor exacto do enum ganha sempre."""
    from otm_core_schema.enums import ComponentKind

    for kind in ComponentKind:
        assert _kind(kind.value) == kind.value


def test_o_tipo_mal_lido_silencia_ameacas() -> None:
    """Porque isto importa: o tipo escolhe as heurísticas."""
    from otm_core_schema import ThreatModelDocument
    from otm_threat_engine import analyze_document

    def _threat_ids(kind: str) -> set[str]:
        document = ThreatModelDocument.model_validate(
            {
                "model": {"schema_version": "1.1.0", "system_type": "web_application", "industry_sector": "saas"},
                "metadata": {"title": "Import"},
                "components": [{"id": "c1", "name": "Order business logic", "kind": kind}],
            }
        )
        return {h.id for h in analyze_document(document).heuristic_threats if not h.skipped_as_duplicate}

    silenced = _threat_ids("process") - _threat_ids("queue")

    assert silenced, "premissa: tipificar mal tem de mudar mesmo as ameaças produzidas"
    assert _kind("business-logic") == "process"
