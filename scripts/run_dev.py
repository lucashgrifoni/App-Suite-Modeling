#!/usr/bin/env python3
"""
Sobe a API (uvicorn) e a UI (Vite) em paralelo, usando o Python do ``.venv``.

Requer ``setup_dev.py`` já executado (``.venv`` e ``apps/web/node_modules``).

Uso (na raiz do repositório):

    python scripts/run_dev.py

Encerre com Ctrl+C (termina os dois processos).

Windows e Linux/macOS: mesmo comando.
"""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from dev_env import npm_on_path, npm_popen, repo_root, venv_python


def _terminate(proc: subprocess.Popen | None) -> None:
    if proc is None or proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def main() -> int:
    root = repo_root()
    py = venv_python(root)
    if not py.exists():
        print(
            f"Erro: {py} não existe. Execute primeiro: python scripts/setup_dev.py",
            file=sys.stderr,
        )
        return 1
    if not npm_on_path():
        print("Erro: `npm` não está no PATH.", file=sys.stderr)
        return 1
    web = root / "apps" / "web"
    if not (web / "node_modules").is_dir():
        print(
            f"Aviso: {web / 'node_modules'} ausente; execute npm install em apps/web ou rode setup_dev.py.",
            file=sys.stderr,
        )

    api_cmd = [
        str(py),
        "-m",
        "uvicorn",
        "otm_api.main:app",
        "--reload",
        "--port",
        "8000",
    ]
    print("+ " + " ".join(api_cmd), flush=True)
    print(f"+ npm run dev  (cwd={web})", flush=True)
    print("API: http://127.0.0.1:8000  |  UI: http://localhost:5173  (Ctrl+C para sair)\n", flush=True)

    api: subprocess.Popen | None = None
    web_proc: subprocess.Popen | None = None
    try:
        api = subprocess.Popen(api_cmd, cwd=root)
        web_proc = npm_popen(["run", "dev"], cwd=web)
        while True:
            time.sleep(0.5)
            if api.poll() is not None:
                print("API terminou.", file=sys.stderr)
                break
            if web_proc.poll() is not None:
                print("UI terminou.", file=sys.stderr)
                break
    except KeyboardInterrupt:
        print("\nEncerrando...", flush=True)
    finally:
        _terminate(web_proc)
        _terminate(api)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
