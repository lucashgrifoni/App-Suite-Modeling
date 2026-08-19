"""Recusa publicar um artefacto cuja versão não é a do tag.

Publicar o número errado é o único erro deste pipeline que não se desfaz: o PyPI não reutiliza uma
versão, por isso o engano queima-a para sempre. Daí a verificação correr **antes** do upload, e em
todos os refs que chegam ao job de publicação — não só no evento `release`, porque
`workflow_dispatch` também consegue construir a partir de um ramo qualquer.

A comparação é feita entre versões **normalizadas pela PEP 440**, não entre strings. O gate
anterior comparava texto, e por isso recusava a única forma de release candidate que
`docs/VERSIONING_AND_TAGS.md` prescreve: `vMAJOR.MINOR.PATCH-rcN`. O hífen não pode existir no
campo de versão de um wheel — `-` é o delimitador de campos do nome — e a PEP 440 normaliza
`7.10.0-rc1` para `7.10.0rc1`, pelo que o tag `v7.10.0-rc1` produzia `built=7.10.0rc1` contra
`tag=7.10.0-rc1`, nunca iguais. A mensagem mandava corrigir o `pyproject.toml`, que estaria certo.

Normalizar é **mais correcto, não mais permissivo**, para a falha que isto existe para impedir:
`7.9.0` contra `7.10.0` continua recusado. O que passa a ser aceite são grafias distintas da mesma
versão, que a PEP 440 declara equivalentes — incluindo `7.10` e `7.10.0`, que são a mesma release.
"""

from __future__ import annotations

import os
import pathlib
import sys

from packaging.version import InvalidVersion, Version


class NoWheelBuilt(RuntimeError):
    """Não há wheel para verificar. Um gate sem artefacto tem de recusar, não rebentar."""


def built_version_from_dist(dist_dir: str = "dist") -> str:
    """O campo de versão do wheel construído. `-` é o delimitador do nome, daí o `split`.

    Sem wheel, `next()` levantava `StopIteration` e o passo morria com um traceback em vez de uma
    razão — o mesmo defeito que o shell inline anterior tinha. Um directório `dist/` vazio nunca
    deve ler-se como "nada a objectar".
    """
    wheels = sorted(pathlib.Path(dist_dir).glob("*.whl"))
    if not wheels:
        raise NoWheelBuilt(f"Nenhum wheel em {dist_dir}/ — não há artefacto para verificar nem para publicar.")
    if len(wheels) > 1:
        names = ", ".join(w.name for w in wheels)
        raise NoWheelBuilt(f"Mais do que um wheel em {dist_dir}/ ({names}) — é ambíguo qual seria publicado.")
    return wheels[0].name.split("-")[1]


def refusal_reason(*, built: str, ref_name: str, ref_type: str) -> str | None:
    """`None` quando a publicação pode seguir; caso contrário, a razão para recusar.

    Um ref que não é tag não tem versão contra a qual comparar. Uma dry run a partir de um ramo é
    legítima — o que não é legítimo é publicar a partir dele, e isso é decidido noutro sítio.
    """
    if ref_type != "tag":
        return None

    tag = ref_name.removeprefix("v")

    try:
        tagged = Version(tag)
    except InvalidVersion:
        return (
            f"O tag {ref_name} não contém uma versão PEP 440 ({tag!r} depois de tirar o `v`). "
            "Use `vMAJOR.MINOR.PATCH` ou `vMAJOR.MINOR.PATCH-rcN`."
        )

    try:
        produced = Version(built)
    except InvalidVersion:
        return f"O wheel construído não tem uma versão PEP 440 legível: {built!r}."

    if produced != tagged:
        return f"A versão construída {built} não corresponde ao tag {tag}. Corrija `pyproject.toml` ou refaça o tag."
    return None


def main() -> int:
    ref_type = os.environ.get("GITHUB_REF_TYPE", "")
    ref_name = os.environ.get("GITHUB_REF_NAME", "")

    if ref_type != "tag":
        print("::notice::O ref não é um tag, portanto não há versão para comparar. Este build não deve ser publicado.")
        return 0

    try:
        built = built_version_from_dist()
    except NoWheelBuilt as exc:
        print(f"::error::{exc}")
        return 1
    print(f"built={built} ref={ref_name} ref_type={ref_type}")

    reason = refusal_reason(built=built, ref_name=ref_name, ref_type=ref_type)
    if reason is not None:
        print(f"::error::{reason}")
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - ponto de entrada do workflow
    sys.exit(main())
