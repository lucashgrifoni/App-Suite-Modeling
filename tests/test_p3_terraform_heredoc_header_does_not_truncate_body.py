"""Um cabeçalho `resource` dentro de um heredoc não pode encurtar o bloco que o contém.

`_iter_resource_blocks` limita a varredura de chavetas ao cabeçalho seguinte para que um ficheiro
com chavetas em falta não custe O(L*M) -- ver a docstring da função. O limite assume que **todo**
o texto que casa com `_RESOURCE_HEAD` é um cabeçalho verdadeiro, e num heredoc não é: o corpo do
bloco exterior passa a terminar no texto citado, e tudo o que venha depois desaparece dele.

O que desaparece importa: `_public_ingress_hint` é o único consumidor do corpo, e um `0.0.0.0/0`
declarado depois do heredoc deixa de ser visto. Um `aws_lb` mapeia para `GATEWAY`, por isso o
efeito é mover um balanceador exposto de `tb_internet_facing` para a fronteira interna -- a mesma
classificação errada que o limite foi introduzido para evitar, na direcção oposta.

O ficheiro deste teste tem as chavetas equilibradas: não depende de HCL inválido.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "artifact-import"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

_HCL = """
resource "aws_lb" "front" {
  user_data = <<EOT
resource "aws_instance" "demo" {
  ami = "ami-123"
}
EOT
  ingress {
    cidr_blocks = ["0.0.0.0/0"]
  }
}
"""


def test_o_hcl_do_caso_esta_equilibrado() -> None:
    """Sanidade: sem isto o teste provaria apenas que HCL inválido se comporta mal."""
    assert _HCL.count("{") == _HCL.count("}")


def test_o_corpo_do_bloco_exterior_chega_ao_cidr_declarado_depois_do_heredoc() -> None:
    from otm_artifact_import.terraform_import import _iter_resource_blocks, _public_ingress_hint

    bodies = {f"{t}.{n}": b for t, n, b in _iter_resource_blocks(_HCL)}

    assert "aws_lb.front" in bodies
    assert _public_ingress_hint(bodies["aws_lb.front"]), (
        "o corpo do `aws_lb.front` foi truncado no cabeçalho citado dentro do heredoc, "
        "por isso o `0.0.0.0/0` que vem depois dele desapareceu"
    )


def test_o_balanceador_exposto_fica_na_fronteira_externa() -> None:
    from otm_artifact_import.terraform_import import import_terraform_text

    result = import_terraform_text(_HCL)
    doc = result.document

    front = next(c for c in doc.components if c.name == "aws_lb.front")
    external = {b.id for b in doc.trust_boundaries if "internet" in b.id.lower()}

    assert external, "o documento não declara nenhuma fronteira internet-facing"
    assert front.in_trust_boundary in external, (
        f"balanceador com `0.0.0.0/0` classificado em `{front.in_trust_boundary}` em vez de uma de {sorted(external)}"
    )
