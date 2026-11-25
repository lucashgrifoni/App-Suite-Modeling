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


def npm_command() -> list[str]:
    """Resolve um comando npm que possa receber argumentos sem passar por um shell."""
    if sys.platform == "win32":
        executable = shutil.which("npm.exe")
        if executable:
            return [executable]

        shim = shutil.which("npm.cmd")
        if shim:
            directory = Path(shim).parent
            cli = directory / "node_modules" / "npm" / "bin" / "npm-cli.js"
            node = directory / "node.exe"
            node_executable = str(node) if node.is_file() else shutil.which("node.exe")
            if node_executable and cli.is_file():
                return [node_executable, str(cli)]
    else:
        executable = shutil.which("npm")
        if executable:
            return [executable]

    raise FileNotFoundError("npm não encontrado no PATH com um executável ou uma instalação Node.js utilizável")


def npm_on_path() -> bool:
    """Indica se existe um comando npm utilizável."""
    try:
        npm_command()
    except FileNotFoundError:
        return False
    return True


def npm_run(args: list[str], *, cwd: Path) -> None:
    """Executa npm e propaga falhas do comando."""
    subprocess.run([*npm_command(), *args], cwd=cwd, check=True)


def npm_popen(args: list[str], *, cwd: Path) -> subprocess.Popen:
    """Como ``npm_run``, mas devolve um ``Popen`` (servidor de desenvolvimento)."""
    return subprocess.Popen([*npm_command(), *args], cwd=cwd)
