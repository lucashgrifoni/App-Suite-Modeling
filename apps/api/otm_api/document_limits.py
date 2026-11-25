"""
Tecto opcional de entidades para um documento submetido — o único limite de **saída** que
esta API pode ter sem inventar um número.

A entrada já é limitada em vários eixos (bytes do ficheiro, nós YAML expandidos, profundidade,
2 MiB por upload em `/v1/imports`). A saída não era limitada em nenhum: o motor produz da
ordem de sete ameaças por componente, cada uma um objeto completo com referências de
framework, e o `AnalysisResult` inteiro é serializado numa resposta construída em memória
antes do primeiro byte sair. Medido em `/v1/models/analyze`:

    componentes   pedido      resposta    razão
          1 005    490 KB      10,5 MB    22,0x
          2 005    974 KB      21,0 MB    22,1x
          4 005  1 943 KB      42,1 MB    22,2x

A razão é constante, ou seja a amplificação é **linear**: o limite de corpo do gateway que
`docs/architecture/DEPLOYMENT_INVARIANTS.md` já torna obrigatório *consegue* delimitar a
resposta — desde que o operador saiba por quanto multiplicar, número que `docs/features/API.md`
passa a publicar.

Por que razão não há default
----------------------------
Um tecto por omissão teria de estar na ordem dos milhares para limitar alguma coisa, e é
exatamente aí que recusaria trabalho legítimo: um upload Terraform de 1,64 MiB — aceite pelo
limite de 2 MiB da própria rota `/v1/imports` — produz um rascunho com **30 001 componentes**,
e `analyze` responde hoje a 4 005 componentes em 3,6 s. Um tecto por omissão transformaria o
caminho `import -> analyze` que o produto anuncia num 413. Trocar "sem tecto" por "recusa
entrada válida" seria trocar um defeito por outro, por isso o tecto existe, é explícito, e
quem o liga escolhe o número para a sua capacidade.

O tecto vive no funil `routers/_errors.document_from_payload_or_422`, por onde passam todas as
rotas que recebem um documento (`/v1/models/*`, `/v1/exports`, `/v1/remediation/backlog`,
`/v1/reports`, `/v1/reports/premium`) e **nenhuma** rota de importação.
"""

from __future__ import annotations

import os

from otm_core_schema import ThreatModelDocument

#: Tecto de entidades (`components` + `data_flows` + `assets`) por documento submetido.
#: Por definir = sem tecto, que é o comportamento histórico.
ENV_MAX_DOCUMENT_ENTITIES = "OTM_MAX_DOCUMENT_ENTITIES"


class DocumentLimitConfigError(ValueError):
    """``OTM_MAX_DOCUMENT_ENTITIES`` tem um valor que não é um tecto utilizável."""


def resolve_max_document_entities() -> int | None:
    """
    O tecto configurado, ou ``None`` quando não há nenhum.

    Vazio conta como ausente (secret de CI que resolveu para nada, linha `.env` com um espaço),
    porque a alternativa — ler o vazio como `0` — recusaria todos os documentos, incluindo os
    que não têm uma única entidade. Um valor que não é um inteiro positivo é recusado com um
    erro nomeado, como `OTM_ENV`, `OTM_TRUSTED_PROXY`, `OTM_LOG_LEVEL` e `OTM_MAX_YAML_NODES`
    já fazem: `main.py` resolve-o no arranque, por isso uma gralha aborta o deploy em vez de
    aparecer como um 500 no primeiro pedido com documento.
    """
    raw = (os.environ.get(ENV_MAX_DOCUMENT_ENTITIES) or "").strip()
    if not raw:
        return None
    try:
        ceiling = int(raw)
    except ValueError as exc:
        raise DocumentLimitConfigError(
            f"{ENV_MAX_DOCUMENT_ENTITIES}={raw!r} is not an integer. Set the maximum number of "
            "components + data flows + assets a submitted document may carry, or unset the "
            "variable to accept any size."
        ) from exc
    if ceiling < 1:
        raise DocumentLimitConfigError(
            f"{ENV_MAX_DOCUMENT_ENTITIES}={raw!r} would refuse every document, including empty "
            "ones. Set a positive ceiling, or unset the variable to accept any size."
        )
    return ceiling


def count_document_entities(document: ThreatModelDocument) -> int:
    """As três coleções que determinam o fan-out do motor, e portanto o tamanho da resposta."""
    return len(document.components) + len(document.data_flows) + len(document.assets)
