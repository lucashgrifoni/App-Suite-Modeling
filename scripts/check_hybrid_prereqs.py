"""
Pré-requisitos para `npm run e2e:hybrid` (Playwright + uvicorn + otm_api).

Uso (raiz do repositório):
    python scripts/check_hybrid_prereqs.py

Código 0 se `otm_api` é importável; 1 com mensagem acionável.
"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        import otm_api.main  # noqa: F401
    except ImportError as e:
        print(
            "[e2e:hybrid] Falta o pacote da API. Na raiz do repo execute:\n"
            "  pip install -e \".[dev,cli,api]\"\n"
            "Garanta também Python 3.12+ no PATH usado pelo npm.",
            file=sys.stderr,
        )
        print(e, file=sys.stderr)
        return 1
    print("[e2e:hybrid] OK — módulo otm_api importável.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
