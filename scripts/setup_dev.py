#!/usr/bin/env python3
"""
Cria o ambiente virtual, instala o pacote em modo editável (dev+cli+api) e ``npm install`` na UI.

Uso (na raiz do repositório):

    python scripts/setup_dev.py

Opções:

    python scripts/setup_dev.py --skip-npm
    python scripts/setup_dev.py --recreate-venv

Windows e Linux/macOS: mesmo comando; caminhos do venv são resolvidos automaticamente.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# Permite `python scripts/setup_dev.py` a partir da raiz (dev_env em scripts/).
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from dev_env import VENV_DIR, npm_on_path, npm_run, repo_root, venv_python


MIN_PY = (3, 11)


def _ensure_python_version() -> None:
    if sys.version_info[:2] < MIN_PY:
        print(
            f"Erro: é necessário Python {MIN_PY[0]}.{MIN_PY[1]}+ (encontrado {sys.version_info.major}.{sys.version_info.minor}).",
            file=sys.stderr,
        )
        sys.exit(1)


def _run(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    print(f"+ {' '.join(cmd)}", flush=True)
    subprocess.run(cmd, cwd=cwd, env=env, check=True)


def _create_venv(root: Path, *, recreate: bool) -> None:
    vdir = root / VENV_DIR
    if recreate and vdir.exists():
        print(f"Removendo {vdir} (--recreate-venv)", flush=True)
        shutil.rmtree(vdir)
    if not vdir.exists():
        _run([sys.executable, "-m", "venv", str(vdir)], cwd=root)


def _pip_install_editable(root: Path) -> None:
    # Usar sempre ``python -m pip``: no Windows, invocar ``pip.exe`` para
    # atualizar o próprio pip falha (mensagem a recomendar ``python -m pip``).
    py = venv_python(root)
    if not py.exists():
        print(f"Erro: Python do venv não encontrado em {py}", file=sys.stderr)
        sys.exit(1)
    _run(
        [str(py), "-m", "pip", "install", "--upgrade", "pip"],
        cwd=root,
    )
    _run(
        [str(py), "-m", "pip", "install", "-e", ".[dev,cli,api]"],
        cwd=root,
    )


def _npm_install_web(root: Path) -> None:
    if not npm_on_path():
        print("Aviso: `npm` não está no PATH; a etapa da UI foi ignorada.", file=sys.stderr)
        return
    web = root / "apps" / "web"
    if not web.is_dir():
        print(f"Aviso: pasta da UI inexistente: {web}", file=sys.stderr)
        return
    print("+ npm install", flush=True)
    npm_run(["install"], cwd=web)


def main() -> int:
    parser = argparse.ArgumentParser(description="Setup de desenvolvimento (venv + pip + npm).")
    parser.add_argument(
        "--skip-npm",
        action="store_true",
        help="Não executar npm install em apps/web.",
    )
    parser.add_argument(
        "--recreate-venv",
        action="store_true",
        help="Apagar .venv e criar de novo.",
    )
    args = parser.parse_args()
    _ensure_python_version()
    root = repo_root()
    _create_venv(root, recreate=args.recreate_venv)
    _pip_install_editable(root)
    if not args.skip_npm:
        _npm_install_web(root)

    py = venv_python(root)
    print("", flush=True)
    print("Setup concluído.", flush=True)
    print("Ative o venv e suba API + UI:", flush=True)
    if sys.platform == "win32":
        print(f"  {root}\\.venv\\Scripts\\activate", flush=True)
    else:
        print(f"  source {root}/.venv/bin/activate", flush=True)
    print("  uvicorn otm_api.main:app --reload --port 8000", flush=True)
    print("  (outro terminal) cd apps/web && npm run dev", flush=True)
    print(f"Ou: python scripts/run_dev.py  (usa {py})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
