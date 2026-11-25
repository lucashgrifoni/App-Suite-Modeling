"""P5 — o gate de versão-vs-tag recusava a única forma de RC que a própria documentação prescreve.

`publish-pypi.yml` comparava duas strings: o campo de versão do nome do wheel contra
`${GITHUB_REF_NAME#v}`. A PEP 440 normaliza `7.10.0-rc1` para `7.10.0rc1`, e o hífen não pode
sequer existir num nome de wheel, porque `-` é o delimitador de campos. Logo o tag prescrito em
`docs/VERSIONING_AND_TAGS.md:13` (`vMAJOR.MINOR.PATCH-rcN`) produzia `built=7.10.0rc1` contra
`tag=7.10.0-rc1`: nunca iguais. A primeira release candidate que alguém tentasse era recusada com
"Bump pyproject.toml or retag" — apontando o dedo ao `pyproject.toml`, que estaria correcto.

Verificado no histórico antes de corrigir: **nenhuma RC foi alguma vez publicada** neste
repositório (21 tags, nenhuma com `rc`), por isso o defeito nunca disparou. A outra forma que o
gate também rejeita, `v.7.4`, é histórica e não prescritiva — as onze tags dessa forma são todas
anteriores a 2026-05-28 e o gate só existe desde 2026-08-05, portanto nunca se cruzaram. A
contradição viva é só a das RC.

**Comparar versões normalizadas é mais correcto, não mais permissivo, para a falha que o gate
existe para impedir**: publicar um wheel cuja versão não é a do tag queima um número no PyPI para
sempre. `7.9.0` contra `7.10.0` continua a ser recusado — é o que os testes de recusa abaixo
fixam. O que passa a ser aceite são grafias diferentes da *mesma* versão, que a PEP 440 define
como equivalentes.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "check_release_version_matches_tag.py"


def _module() -> Any:
    spec = importlib.util.spec_from_file_location("check_release_version_matches_tag", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _refusal(built: str, ref_name: str, ref_type: str = "tag") -> str | None:
    return _module().refusal_reason(built=built, ref_name=ref_name, ref_type=ref_type)


# ---------------------------------------------------------------- o defeito


def test_a_forma_de_rc_documentada_passa_a_ser_aceite() -> None:
    """`vMAJOR.MINOR.PATCH-rcN` é o que `VERSIONING_AND_TAGS.md` prescreve."""
    assert _refusal("7.10.0rc1", "v7.10.0-rc1") is None


@pytest.mark.parametrize("tag", ["v7.10.0rc1", "v7.10.0-rc1", "v7.10.0.rc1", "v7.10.0RC1"])
def test_as_grafias_equivalentes_da_mesma_rc_sao_todas_aceites(tag: str) -> None:
    """A PEP 440 define-as como a mesma versão; recusar uma delas é um falso positivo."""
    assert _refusal("7.10.0rc1", tag) is None


# ------------------------------------------------- o gate não pode enfraquecer


@pytest.mark.parametrize(
    ("built", "tag"),
    [
        ("7.9.0", "v7.10.0"),
        ("7.10.0", "v7.9.0"),
        ("7.10.0", "v7.10.1"),
        ("7.10.0rc1", "v7.10.0"),
        ("7.10.0", "v7.10.0rc1"),
    ],
)
def test_uma_divergencia_genuina_continua_a_ser_recusada(built: str, tag: str) -> None:
    """A falha que o gate existe para impedir: um número do PyPI queima-se para sempre."""
    reason = _refusal(built, tag)

    assert reason is not None
    assert built in reason and tag.lstrip("v") in reason


def test_a_versao_estavel_normal_continua_a_passar() -> None:
    assert _refusal("7.9.0", "v7.9.0") is None


def test_zeros_finais_sao_a_mesma_versao() -> None:
    """`7.10` e `7.10.0` são a mesma release em PEP 440; aceitar não admite publicação errada."""
    assert _refusal("7.10.0", "v7.10") is None


# ------------------------------------------------------------ casos de erro


def test_um_tag_que_nao_e_uma_versao_e_recusado_com_uma_razao_legivel() -> None:
    """`v.7.4` dá `.7.4`, que não é uma versão. Recusar é certo; rebentar não."""
    reason = _refusal("7.4.0", "v.7.4")

    assert reason is not None
    assert ".7.4" in reason


def test_um_wheel_com_versao_ilegivel_e_recusado() -> None:
    reason = _refusal("nao-e-uma-versao", "v7.9.0")

    assert reason is not None


def test_um_ref_que_nao_e_tag_nao_tem_versao_para_comparar() -> None:
    """Uma dry run a partir de um ramo é legítima; publicar a partir dele não é."""
    assert _refusal("7.9.0", "main", ref_type="branch") is None


def test_o_script_expoe_um_main_para_o_workflow_chamar() -> None:
    assert callable(_module().main)


def test_um_dist_vazio_recusa_em_vez_de_rebentar(tmp_path: Path) -> None:
    """Um gate sem artefacto tem de recusar. `next()` cru dava `StopIteration` e um traceback."""
    module = _module()

    with pytest.raises(module.NoWheelBuilt, match="Nenhum wheel"):
        module.built_version_from_dist(str(tmp_path))


def test_dois_wheels_sao_ambiguos_e_tambem_recusam(tmp_path: Path) -> None:
    """Qual deles seria publicado? Escolher em silêncio é a resposta errada."""
    (tmp_path / "open_threat_model-7.9.0-py3-none-any.whl").write_bytes(b"")
    (tmp_path / "open_threat_model-7.10.0-py3-none-any.whl").write_bytes(b"")
    module = _module()

    with pytest.raises(module.NoWheelBuilt, match="Mais do que um wheel"):
        module.built_version_from_dist(str(tmp_path))


def test_um_dist_com_um_wheel_devolve_a_versao(tmp_path: Path) -> None:
    (tmp_path / "open_threat_model-7.9.0-py3-none-any.whl").write_bytes(b"")

    assert _module().built_version_from_dist(str(tmp_path)) == "7.9.0"
