"""O sinal de privacidade estava invertido: LGPD não contava, "privilegiado" contava.

`_build_fit_context` compara a `description` com `pii`/`lgpd`/`gdpr`/`dados pessoais`, e o
`regulatory_context` **só** com `"priv"`. Como subcadeia, `"priv"` casa com *privilegiado* — acesso
privilegiado, que não tem nada que ver com privacidade — e não casa com LGPD nem GDPR.

Medido, variando só o `regulatory_context`:

    "LGPD, dados pessoais de titulares"     sinal = False
    "GDPR Article 32"                       sinal = False
    "Acesso privilegiado auditado (SOX)"    sinal = True

As duas regulações de privacidade mais óbvias do mercado deste produto não contam, e um controlo de
acesso conta. O sinal alimenta a matriz de adequação de metodologias e, por ela, o pré-check de
qualidade publicado ao utilizador.

Os dois campos passam a ser lidos com o mesmo vocabulário. Os acrónimos pedem fronteira dos dois
lados; `privacidade` e `privacy` entram como radicais próprios, em vez do `priv` solto que colidia
com privilégio.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "industry-packs", "framework-mappings"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))


def _privacy_cue(*, description: str = "Servico interno de acesso.", regulatory: str = "") -> bool:
    from otm_core_schema import ThreatModelDocument
    from otm_core_schema.methodology_fit_matrix import _build_fit_context

    document = ThreatModelDocument.model_validate(
        {
            "model": {"schema_version": "1.1.0", "methodology": "linddun"},
            "metadata": {"title": "Servico interno", "tags": []},
            "components": [{"id": "svc", "name": "Servico", "kind": "process"}],
            "business_context": {"description": description, "regulatory_context": regulatory},
        }
    )
    return _build_fit_context(document).has_privacy_cue


@pytest.mark.parametrize(
    "regulatory",
    ["LGPD, dados pessoais de titulares", "GDPR Article 32", "Sujeito a LGPD", "Privacidade por desenho"],
)
def test_uma_regulacao_de_privacidade_conta(regulatory: str) -> None:
    assert _privacy_cue(regulatory=regulatory), f"`{regulatory}` não contou como privacidade"


@pytest.mark.parametrize(
    "regulatory",
    ["Acesso privilegiado auditado (SOX)", "Gestao de contas privilegiadas", "Privilege escalation review"],
)
def test_acesso_privilegiado_nao_e_privacidade(regulatory: str) -> None:
    assert not _privacy_cue(regulatory=regulatory), f"`{regulatory}` contou como privacidade"


def test_a_descricao_continua_a_contar() -> None:
    """Não-regressão: o campo que já era lido tem de continuar a ser."""
    assert _privacy_cue(description="Tratamos dados pessoais de clientes.")
    assert _privacy_cue(description="Sistema sujeito a GDPR.")


def test_um_contexto_neutro_nao_conta() -> None:
    assert not _privacy_cue(regulatory="ISO 27001 e continuidade de negocio")
