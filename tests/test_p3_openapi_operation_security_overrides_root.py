"""Um `security: []` numa operação anula o requisito global — e o importador tem de o ver.

A especificação OpenAPI é explícita: `security` numa operação **substitui** o do documento, e uma
lista vazia remove a exigência para essa operação. `_infer_authenticated` consultava a raiz
primeiro e devolvia `True` sem sequer olhar para as operações, o que a sua própria docstring
declarava como regra: *"segurança global > consenso por operação"*.

Consequência medida: uma spec cuja raiz exige `bearerAuth` e cujas operações **todas** declaram
`security: []` — isto é, uma API inteiramente aberta — produzia um fluxo `authenticated=True`,
indistinguível da spec em que as operações herdam o requisito. O modelo de ameaças afirmava o
contrário da verdade sobre a única propriedade de segurança que este importador infere, e fá-lo
na direcção que **esconde** exposição.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "artifact-import"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

_HEAD = 'openapi: 3.0.0\ninfo: {title: t, version: "1"}\n'
_ROOT_SECURITY = "security:\n  - bearerAuth: []\n"


def _spec(*, root_security: bool, operations: list[str]) -> str:
    body = "paths:\n"
    for index, declaration in enumerate(operations):
        body += f"  /p{index}:\n    get:\n"
        if declaration:
            body += f"      {declaration}\n"
        body += '      responses: {"200": {description: ok}}\n'
    return _HEAD + (_ROOT_SECURITY if root_security else "") + body


def _authenticated(spec: str) -> bool | None:
    from otm_artifact_import.openapi_import import import_openapi_text

    flows = import_openapi_text(spec).document.data_flows
    assert flows, "a spec não produziu fluxo nenhum"
    return flows[0].authenticated


def test_a_raiz_sozinha_continua_a_autenticar() -> None:
    """Não-regressão: operações silenciosas herdam o requisito global."""
    assert _authenticated(_spec(root_security=True, operations=["", ""])) is True


def test_todas_as_operacoes_a_renunciar_nao_e_autenticado() -> None:
    spec = _spec(root_security=True, operations=["security: []", "security: []"])

    assert _authenticated(spec) is not True, (
        "spec cuja raiz exige token e cujas operações todas o dispensam classificada como autenticada"
    )


def test_uma_operacao_a_renunciar_ja_quebra_o_consenso() -> None:
    """`all`, não `any`: basta um caminho aberto para a API não ser toda autenticada."""
    spec = _spec(root_security=True, operations=["", "security: []"])

    assert _authenticated(spec) is not True


def test_operacoes_a_exigir_sem_raiz_continuam_autenticadas() -> None:
    spec = _spec(root_security=False, operations=["security:\n        - bearerAuth: []"])

    assert _authenticated(spec) is True


def test_sem_seguranca_declarada_continua_indeterminado() -> None:
    """Ausência de declaração não é o mesmo que renúncia explícita, e não pode passar a sê-lo."""
    assert _authenticated(_spec(root_security=False, operations=["", ""])) is None


@pytest.mark.parametrize("root_security", [True, False])
def test_uma_spec_sem_operacoes_nao_rebenta(root_security: bool) -> None:
    from otm_artifact_import.openapi_import import import_openapi_text

    import_openapi_text(_HEAD + (_ROOT_SECURITY if root_security else "") + "paths: {}\n")
