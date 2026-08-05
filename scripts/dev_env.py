"""
Funções partilhadas para setup e execução de desenvolvimento (Windows e POSIX).

Mantém um único sítio para caminhos do venv e raiz do repositório.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

# Nome do diretório do venv na raiz do repositório (alinhado com a documentação).
VENV_DIR = ".venv"


def repo_root() -> Path:
    """Raiz do repositório (pai de ``scripts/``)."""
    return Path(__file__).resolve().parent.parent


def venv_python(repo: Path | None = None) -> Path:
    """Interpretador Python dentro de ``.venv`` para o SO atual."""
    root = repo or repo_root()
    if sys.platform == "win32":
        return root / VENV_DIR / "Scripts" / "python.exe"
    return root / VENV_DIR / "bin" / "python"


def venv_pip(repo: Path | None = None) -> Path:
    """Executável pip dentro do venv."""
    root = repo or repo_root()
    if sys.platform == "win32":
        return root / VENV_DIR / "Scripts" / "pip.exe"
    return root / VENV_DIR / "bin" / "pip"


def npm_on_path() -> bool:
    """Indica se ``npm`` parece disponível (``npm`` ou ``npm.cmd`` no PATH)."""
    return bool(shutil.which("npm") or (sys.platform == "win32" and shutil.which("npm.cmd")))


def npm_run(args: list[str], *, cwd: Path) -> None:
    """
    Executa ``npm`` com ``subprocess.run`` (ex.: ``["install"]``, ``["run", "dev"]``).

    No Windows usa ``shell=True`` e uma linha de comando para o ``cmd.exe`` resolver
    ``npm.cmd``; invocar o caminho devolvido por ``which("npm")`` como executável
    pode provocar ``OSError: [WinError 193]`` com shims sem extensão ``.exe``.
    """
    if sys.platform == "win32":
        line = "npm " + subprocess.list2cmdline(args)
        # Triado e aceite: script só de desenvolvimento, `args` são literais do próprio repo
        # (`["install"]`, `["run", "dev"]`), nunca entrada externa. O `shell=True` existe pela
        # razão documentada acima e não por conveniência.
        # Ambos os ids são precisos: o curto é a regra deste repo, o longo é a da comunidade
        # (`p/security-audit`). Durante muito tempo só o curto estava aqui, por isso a regra
        # da comunidade nunca foi suprimida — e ninguém reparou porque o filtro de severidade
        # do gate a estava a descartar antes de chegar a correr.
        # O `nosemgrep` fica na linha do `shell=True` porque é aí que a regra da comunidade
        # reporta — não na linha da chamada. Pô-lo no sítio errado dá uma suppressão que
        # parece existir e não suprime nada.
        subprocess.run(  # nosemgrep: python-subprocess-shell-true
            line,
            cwd=cwd,
            shell=True,  # nosemgrep: python.lang.security.audit.subprocess-shell-true.subprocess-shell-true
            check=True,
        )
        return
    npm = shutil.which("npm")
    if not npm:
        raise FileNotFoundError("npm não encontrado no PATH")
    subprocess.run([npm, *args], cwd=cwd, check=True)


def npm_popen(args: list[str], *, cwd: Path) -> subprocess.Popen:
    """Como ``npm_run``, mas devolve um ``Popen`` (servidor de desenvolvimento)."""
    if sys.platform == "win32":
        line = "npm " + subprocess.list2cmdline(args)
        # Mesma triagem e mesmos dois ids que `npm_run` acima.
        return subprocess.Popen(  # nosemgrep: python-subprocess-shell-true
            line,
            cwd=cwd,
            shell=True,  # nosemgrep: python.lang.security.audit.subprocess-shell-true.subprocess-shell-true
        )
    npm = shutil.which("npm")
    if not npm:
        raise FileNotFoundError("npm não encontrado no PATH")
    return subprocess.Popen([npm, *args], cwd=cwd)
