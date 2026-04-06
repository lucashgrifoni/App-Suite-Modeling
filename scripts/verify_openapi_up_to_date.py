"""
Verifica se `contracts/openapi.json` está alinhado com `app.openapi()` (anti-stale).

Uso (raiz do repositório, com `otm_api` instalado):
    python scripts/verify_openapi_up_to_date.py

Saída: código 0 se atualizado; 1 se desatualizado (regenerar com `python scripts/export_openapi.py`).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _canonical_json(obj: object) -> str:
    """Serialização estável para comparação byte-a-byte."""
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def main() -> int:
    repo = Path(__file__).resolve().parents[1]
    path = repo / "contracts" / "openapi.json"
    if not path.is_file():
        print("Falta contracts/openapi.json — execute python scripts/export_openapi.py", file=sys.stderr)
        return 1
    try:
        from otm_api.main import app
    except ImportError as e:
        print("Instale o pacote em modo editável: pip install -e '.[api]'", file=sys.stderr)
        print(e, file=sys.stderr)
        return 1
    fresh = app.openapi()
    committed = json.loads(path.read_text(encoding="utf-8"))
    if _canonical_json(fresh) != _canonical_json(committed):
        print(
            "contracts/openapi.json está DESATUALIZADO em relação ao FastAPI.\n"
            "Execute: python scripts/export_openapi.py\n"
            "Depois: cd apps/web && npm run contracts:generate",
            file=sys.stderr,
        )
        return 1
    print("OpenAPI em disco está sincronizado com o código.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
