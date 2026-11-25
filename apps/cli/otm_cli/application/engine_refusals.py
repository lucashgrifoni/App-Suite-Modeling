"""Recusas do motor traduzidas para a convenção de erro do CLI.

O motor recusa um documento cujos ids de ameaça colidem (ver `assert_threat_ids_are_injective`).
A recusa é deliberada e a entrada é corrigível por quem a escreveu, mas escapava como excepção
não tratada: `otm analyze` despejava um traceback do Python -- que imprime o caminho absoluto de
quem corre o comando -- em vez do `Failure: / Likely cause: / Next step:` que o mesmo comando já
produz para um pack inexistente.

Um único tradutor, e não um `try` repetido em cada serviço, porque são cinco os caminhos que
chamam o motor (`analyze`, `report`, `backlog`, `diff` de dois lados) e o sexto que vier herda-o
de graça.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from otm_threat_engine import ThreatIdCollisionError

from otm_cli.shared.errors import CliUserError


@contextmanager
def engine_refusals_as_cli_errors(*, failed: str) -> Iterator[None]:
    """`failed` nomeia a operação em curso, como nos outros erros do CLI."""
    try:
        yield
    except ThreatIdCollisionError as e:
        raise CliUserError(
            failed=failed,
            cause=(f"the threat id `{e.threat_id}` is claimed by two different subjects: {e.first} and {e.second}."),
            next_step=(
                "rename one of the two subjects so the ids no longer collide — threat ids are "
                "built by joining the subject id with `_`, so these two are indistinguishable "
                "to the drift gate, the analysis diff and the SARIF fingerprints."
            ),
        ) from e
