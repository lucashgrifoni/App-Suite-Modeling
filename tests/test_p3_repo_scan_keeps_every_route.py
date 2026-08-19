"""`otm import repo` não pode perder rotas — é a superfície que ele existe para descobrir.

`_dedupe_inferences` remove duplicados por `(kind, message)`. A mensagem da rota JavaScript é
`Rota HTTP encontrada em \`app.js\`` — igual para **todas** as rotas do mesmo ficheiro, porque o
caminho vive só no `evidence`. Quatro rotas declaradas, uma sobrevive.

A irmã Python, quatro linhas acima no mesmo ficheiro, escreve
`Rota FastAPI/Starlette provável \`/diff\` em \`...\`` — com o caminho. É a mensagem JS que está
fora do padrão, e é por isso que a varredura deste próprio repositório (Python) devolve as 16
rotas sem colapsar nenhuma.

O que se perde não é decorativo: no caso reproduzido sobrevivia `/health` e desapareciam `/login`,
`/admin/users` e `/accounts/:id` — exactamente as que interessam a um modelo de ameaças.

Duas defesas, porque tratam coisas diferentes: a mensagem passa a nomear a rota (é o que o
utilizador lê), e a chave de deduplicação passa a incluir a evidência (rede de segurança para a
próxima inferência cuja mensagem omita o que a distingue). Medido: incluir a evidência na chave
não muda nada na varredura deste repositório, 43 inferências antes e depois.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
for _pkg in ("core-schema", "threat-engine", "artifact-import"):
    sys.path.insert(0, str(_ROOT / "packages" / _pkg))

_APP_JS = """const express = require('express');
const app = express();
app.get('/health', (req, res) => res.send('ok'));
app.post('/login', (req, res) => res.send('login'));
app.get('/admin/users', (req, res) => res.send('users'));
app.delete('/accounts/:id', (req, res) => res.send('deleted'));
module.exports = app;
"""

_ROUTES = ["/health", "/login", "/admin/users", "/accounts/:id"]


def _scan(root: Path) -> list[dict]:
    from otm_artifact_import.repo_scan import scan_node_express_repo

    return scan_node_express_repo(root)["inferences"]


def _write_repo(tmp_path: Path, source: str) -> Path:
    (tmp_path / "app.js").write_text(source, encoding="utf-8")
    return tmp_path


def test_o_ficheiro_do_caso_declara_quatro_rotas() -> None:
    """Sanidade: o teste seguinte não pode passar por não haver rotas para perder."""
    assert sum(_APP_JS.count(f"'{route}'") for route in _ROUTES) == len(_ROUTES)


def test_todas_as_rotas_do_ficheiro_sobrevivem(tmp_path: Path) -> None:
    inferences = _scan(_write_repo(tmp_path, _APP_JS))
    routes = [i for i in inferences if i.get("kind") == "route"]

    found = {i.get("evidence") for i in routes}
    missing = [route for route in _ROUTES if route not in found]

    assert not missing, f"rotas declaradas e ausentes do resultado: {missing} (obtidas: {sorted(found)})"


def test_a_mensagem_nomeia_a_rota(tmp_path: Path) -> None:
    """O utilizador lê a mensagem, não a evidência — e mensagens iguais não se distinguem."""
    routes = [i for i in _scan(_write_repo(tmp_path, _APP_JS)) if i.get("kind") == "route"]

    messages = [i.get("message", "") for i in routes]
    assert len(set(messages)) == len(messages), f"mensagens repetidas entre rotas distintas: {messages}"
    for route in _ROUTES:
        assert any(route in message for message in messages), f"nenhuma mensagem nomeia `{route}`: {messages}"


def test_uma_rota_mesmo_repetida_continua_a_deduplicar(tmp_path: Path) -> None:
    """A correcção não podia ser desligar a deduplicação."""
    duplicated = _APP_JS + "app.get('/health', (req, res) => res.send('again'));\n"
    routes = [i for i in _scan(_write_repo(tmp_path, duplicated)) if i.get("kind") == "route"]

    health = [i for i in routes if i.get("evidence") == "/health"]
    assert len(health) == 1, f"`/health` declarada duas vezes devia aparecer uma: {health}"
