"""A forma-directório do `import` declarava só o directório, não os ficheiros que leu.

`_require_output_is_not_a_source` compara a saída com as entradas declaradas. Para
`otm import k8s dir/` e `otm import terraform dir/`, a entrada declarada era o **directório**, e o
guarda não via os manifestos lá dentro:

    otm import k8s manifests/ -o manifests/svc.yaml
    -> exit 0, e 78 bytes de manifesto substituídos por 2 042 de rascunho

O importador tinha acabado de ler esse ficheiro. É a mesma classe do `--rules`, corrigida antes
neste ramo, e do `import repo`, corrigida antes disso.

A enumeração dos ficheiros passou a viver no pacote do importador (`kubernetes_manifest_files`,
`terraform_files`) e é usada pelos dois lados. Repetir o glob no CLI seria duas cópias da mesma
regra, e a que derivasse deixaria de proteger o ficheiro certo.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]

_MANIFEST = "apiVersion: v1\nkind: Service\nmetadata: {name: web}\nspec: {type: LoadBalancer}\n"
_TERRAFORM = 'resource "aws_lb" "front" {\n  internal = true\n}\n'


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - argv fixo, sem shell
        [sys.executable, "-m", "otm_cli.main", *args], capture_output=True, text=True, cwd=str(_ROOT)
    )


@pytest.mark.parametrize(
    ("kind", "name", "body"),
    [("k8s", "svc.yaml", _MANIFEST), ("terraform", "main.tf", _TERRAFORM)],
)
def test_o_rascunho_nao_escreve_por_cima_de_um_ficheiro_lido(tmp_path: Path, kind: str, name: str, body: str) -> None:
    source = tmp_path / name
    source.write_text(body, encoding="utf-8")

    result = _run(["import", kind, str(tmp_path), "-o", str(source)])

    assert result.returncode == 1, f"saiu {result.returncode}: {result.stdout[:200]}"
    assert source.read_text(encoding="utf-8") == body, "o manifesto foi destruído"


@pytest.mark.parametrize(
    ("kind", "name", "body"),
    [("k8s", "svc.yaml", _MANIFEST), ("terraform", "main.tf", _TERRAFORM)],
)
def test_um_destino_fora_dos_ficheiros_lidos_continua_a_ser_escrito(
    tmp_path: Path, kind: str, name: str, body: str
) -> None:
    """A correcção não podia ser recusar toda a escrita para dentro do directório."""
    (tmp_path / name).write_text(body, encoding="utf-8")
    out = tmp_path / "draft.otm.yaml"

    result = _run(["import", kind, str(tmp_path), "-o", str(out)])

    assert result.returncode == 0, result.stdout[:300]
    assert out.exists() and out.stat().st_size > 0


def test_o_helper_e_o_importador_leem_a_mesma_lista(tmp_path: Path) -> None:
    """Uma regra, um sítio: o CLI não repete o glob do importador."""
    sys.path.insert(0, str(_ROOT / "packages" / "artifact-import"))
    sys.path.insert(0, str(_ROOT / "packages" / "core-schema"))
    from otm_artifact_import import kubernetes_manifest_files

    (tmp_path / "a.yaml").write_text(_MANIFEST, encoding="utf-8")
    (tmp_path / "b.yml").write_text(_MANIFEST, encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignorar", encoding="utf-8")

    assert [p.name for p in kubernetes_manifest_files(tmp_path)] == ["b.yml", "a.yaml"]
