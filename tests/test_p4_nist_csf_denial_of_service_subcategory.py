"""O mapeamento de negação de serviço citava a subcategoria de controlo de acesso.

`stride_framework_map.yaml` mapeava `denial_of_service` para `nist_csf | PR.IR-01`, com a nota
*"Resiliência de infraestruturas e recursos (NIST CSF 2.0 PR.IR)."*. A nota descreve a
**categoria** — PR.IR é *Technology Infrastructure Resilience* — mas a **subcategoria** citada é
outra coisa.

Verificado contra a norma publicada, NIST CSWP 29, 26 de Fevereiro de 2024, p. 21
(https://doi.org/10.6028/NIST.CSWP.29), texto extraído do PDF oficial:

    PR.IR-01: Networks and environments are protected from unauthorized logical access and usage
    PR.IR-02: The organization's technology assets are protected from environmental threats
    PR.IR-03: Mechanisms are implemented to achieve resilience requirements in normal and
              adverse situations
    PR.IR-04: Adequate resource capacity to ensure availability is maintained

`PR.IR-01` é controlo de acesso lógico. As irmãs da mesma entrada — ISO A.8.6 (gestão de
capacidade), A.8.14 (redundância), CWE-400 (consumo de recursos sem limite) — mostram que a
intenção era disponibilidade, e as subcategorias que a servem são `PR.IR-03` e `PR.IR-04`.

Isto é uma alegação de conformidade: alguém que use este relatório como evidência de cobertura do
CSF fica a citar um controlo de acesso para uma ameaça de disponibilidade. O teste transcreve o
texto oficial para que trocar o identificador obrigue a trocar a redacção com ele.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT / "packages" / "framework-mappings"))
sys.path.insert(0, str(_ROOT / "packages" / "core-schema"))

#: Texto oficial, NIST CSWP 29 (2024-02-26), p. 21. Transcrito do PDF publicado.
_PR_IR = {
    "PR.IR-01": "networks and environments are protected from unauthorized logical access",
    "PR.IR-02": "technology assets are protected from environmental threats",
    "PR.IR-03": "mechanisms are implemented to achieve resilience requirements",
    "PR.IR-04": "adequate resource capacity to ensure availability is maintained",
}
_AVAILABILITY = {"PR.IR-03", "PR.IR-04"}


def _csf_controls_for(category: str) -> list[str]:
    from otm_core_schema import StrideCategory
    from otm_framework_mappings import default_stride_registry

    refs = default_stride_registry().refs_for_stride(StrideCategory(category))
    return [r.control_id for r in refs if r.framework == "nist_csf"]


def test_a_negacao_de_servico_nao_cita_o_controlo_de_acesso_logico() -> None:
    controls = _csf_controls_for("denial_of_service")

    assert "PR.IR-01" not in controls, (
        "PR.IR-01 é 'networks and environments are protected from unauthorized logical access "
        f"and usage' (CSWP 29, p. 21), não um controlo de disponibilidade: {controls}"
    )


def test_a_negacao_de_servico_cita_uma_subcategoria_de_disponibilidade() -> None:
    controls = _csf_controls_for("denial_of_service")

    assert any(c in _AVAILABILITY for c in controls), (
        f"nenhuma subcategoria de disponibilidade ({sorted(_AVAILABILITY)}) mapeada: {controls}"
    )


def test_toda_a_subcategoria_pr_ir_citada_existe_na_norma() -> None:
    """Um identificador inventado é pior do que um errado: não se descobre a ler a norma."""
    from otm_core_schema import StrideCategory
    from otm_framework_mappings import default_stride_registry

    registry = default_stride_registry()
    unknown = [
        r.control_id
        for category in StrideCategory
        for r in registry.refs_for_stride(category)
        if r.framework == "nist_csf" and r.control_id.startswith("PR.IR") and r.control_id not in _PR_IR
    ]

    assert not unknown, f"subcategorias PR.IR que não existem no CSF 2.0: {sorted(set(unknown))}"
