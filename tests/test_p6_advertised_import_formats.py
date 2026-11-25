"""P6 — a capa não pode anunciar um formato de import que não existe.

Helm era anunciado como formato de import em seis sítios de topo: `README.md` (quatro vezes),
`docs/README.md` e `docs/POSITIONING.md` — este último a comparar o produto com pytm, Threagile,
Threat Dragon e IriusRisk. Não existe `otm import helm`, não existe `/v1/imports/helm`, e a UI não
o oferece. `packages/artifact-import/otm_artifact_import/helm_import.py` existe mas não é alcançável
de lado nenhum.

O documento de detalhe dizia o contrário da capa e estava certo — `docs/features/ARTIFACT_IMPORT.md`
descreve Helm como *"apenas menção quando existe `helm_release` em Terraform; charts não são
expandidos"* e lista "Helm templates/rendering" em "Não suportado (ainda)". Quem lesse a capa
escolhia a ferramenta por uma capacidade que só desmentia ao quarto nível de documentação.

Este teste não fixa Helm. Fixa a regra geral: **cada formato nomeado como importável na capa tem de
ter um caminho real**, seja subcomando do CLI ou rota da API. É a regra que impede a próxima
alegação, não só esta.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

#: Formatos que alguém poderia plausivelmente anunciar, e como cada um se diz nas duas superfícies.
#: A chave é o que aparece na documentação; os valores são os nomes reais a procurar.
_KNOWN_FORMATS = {
    "openapi": ("openapi",),
    "swagger": ("openapi",),
    "kubernetes": ("kubernetes", "k8s"),
    "k8s": ("kubernetes", "k8s"),
    "terraform": ("terraform",),
    "helm": ("helm",),
    "cloudformation": ("cloudformation",),
    "bicep": ("bicep",),
    "ansible": ("ansible",),
    "docker": ("docker",),
}

#: As frases da capa que prometem import. Cada uma é lida à procura de nomes de formato.
_CLAIM_MARKERS = ("import", "Import", "importar")


def _real_import_formats() -> set[str]:
    """O que o produto sabe mesmo importar: rotas da API mais subcomandos do CLI."""
    spec = json.loads((_ROOT / "contracts" / "openapi.json").read_text(encoding="utf-8"))
    routes = {p.rsplit("/", 1)[-1].lower() for p in spec["paths"] if "/imports/" in p}

    cmd = (_ROOT / "apps" / "cli" / "otm_cli" / "commands" / "import_cmd.py").read_text(encoding="utf-8")
    subcommands = set(re.findall(r'@import_app\.command\("([a-z0-9_-]+)"', cmd))

    return {t.lower() for t in routes | subcommands}


def _claimed_formats(path: Path) -> set[str]:
    """Formatos nomeados em linhas que prometem import, na documentação de topo."""
    claimed: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not any(marker in line for marker in _CLAIM_MARKERS):
            continue
        lowered = line.lower()
        for token in _KNOWN_FORMATS:
            if re.search(rf"\b{token}\b", lowered):
                claimed.add(token)
    return claimed


def test_o_produto_importa_pelo_menos_os_tres_formatos_conhecidos() -> None:
    """Sanidade: se isto falhar, o teste abaixo passa por não haver nada para comparar."""
    real = _real_import_formats()

    assert {"openapi", "terraform"} <= real
    assert real & {"kubernetes", "k8s"}


def test_a_capa_nao_anuncia_um_formato_de_import_que_nao_existe() -> None:
    """A regra geral: cada formato prometido tem de ter subcomando ou rota."""
    real = _real_import_formats()
    offenders: dict[str, set[str]] = {}

    for doc in (_ROOT / "README.md", _ROOT / "docs" / "README.md", _ROOT / "docs" / "POSITIONING.md"):
        unsupported = {token for token in _claimed_formats(doc) if not (set(_KNOWN_FORMATS[token]) & real)}
        if unsupported:
            offenders[doc.name] = unsupported

    assert not offenders, f"formatos anunciados sem caminho real: {offenders}"


def test_o_documento_de_detalhe_continua_livre_de_dizer_a_verdade_sobre_helm() -> None:
    """O detalhe pode e deve falar de Helm — como limitação, que é o que ele é.

    A regra é sobre a capa prometer, não sobre a documentação mencionar. Sem este teste, alguém a
    "corrigir" o ficheiro anterior poderia apagar a explicação honesta em vez da promessa falsa.
    """
    detail = (_ROOT / "docs" / "features" / "ARTIFACT_IMPORT.md").read_text(encoding="utf-8").lower()

    assert "helm" in detail, "a explicação de o que Helm faz e não faz não pode desaparecer"
    assert "helm_release" in detail
