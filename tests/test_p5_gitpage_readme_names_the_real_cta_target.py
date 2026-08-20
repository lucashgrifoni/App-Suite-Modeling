"""O README do `gitpage` diz ao dono de um fork um destino que o código não usa.

`gitpage/README.md` afirma que "By default, primary links point to `https://github.com`" e chama
ao passo seguinte "Optional". As duas coisas são falsas ao mesmo tempo:

- `gitpage/src/config/site.ts` fixa `defaultRepoUrl` no repositório **deste** projecto — e o
  comentário no topo do ficheiro explica porquê, porque o fallback neutro anterior era um bug: uma
  CTA morta numa landing page custa mais do que uma errada;
- `.github/workflows/deploy-github-pages.yml` nunca define `VITE_REPO_URL`, portanto o default
  aplica-se sempre.

Quem faça fork e siga o README a acreditar que o passo é opcional publica uma página em que todas
as CTAs — "View on GitHub", "Documentation", "Explore the repository", "Contribute", o link do
rodapé, e `docsReadmeUrl`/`issuesUrl` derivados — apontam ao projecto de outra pessoa.

O código está certo; era a documentação que estava velha. O teste lê o destino **do código** para
que a próxima mudança de um não possa deixar o outro para trás.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_README = _ROOT / "gitpage" / "README.md"
_SITE_CONFIG = _ROOT / "gitpage" / "src" / "config" / "site.ts"


def _default_repo_url() -> str:
    match = re.search(r'defaultRepoUrl\s*=\s*"([^"]+)"', _SITE_CONFIG.read_text(encoding="utf-8"))
    assert match, "não encontrei `defaultRepoUrl` em site.ts"
    return match.group(1)


def test_o_destino_por_omissao_e_um_repositorio_concreto() -> None:
    """Premissa: se o default voltar a ser neutro, é o README que passa a estar certo."""
    url = _default_repo_url()

    assert url.startswith("https://github.com/"), url
    assert url.rstrip("/") != "https://github.com", "o default voltou a ser a homepage do GitHub"


def test_o_readme_nao_promete_um_destino_neutro() -> None:
    text = _README.read_text(encoding="utf-8")

    assert "point to `https://github.com`" not in text, (
        "o README continua a prometer que as CTAs apontam para a homepage do GitHub"
    )


def test_o_readme_nomeia_o_destino_real() -> None:
    text = _README.read_text(encoding="utf-8")

    assert _default_repo_url() in text, (
        f"o README não diz para onde as CTAs apontam por omissão ({_default_repo_url()})"
    )


def test_o_readme_nao_chama_opcional_ao_passo_que_um_fork_tem_de_dar() -> None:
    """`VITE_REPO_URL` não é definido pelo workflow das Pages: para um fork o passo é obrigatório."""
    text = _README.read_text(encoding="utf-8")
    heading = next((line for line in text.splitlines() if "repository urls" in line.lower()), None)

    assert heading, "a secção das URLs do repositório desapareceu"
    assert "optional" not in heading.lower(), f"secção ainda anunciada como opcional: {heading}"
