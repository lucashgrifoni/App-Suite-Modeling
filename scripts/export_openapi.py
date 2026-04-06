"""
Exporta o OpenAPI JSON da app FastAPI para geração de tipos TypeScript.

Uso (na raiz do monorepo, com ambiente que tenha `otm_api` instalado):
    python scripts/export_openapi.py

Saída: contracts/openapi.json (consumido por `openapi-typescript` no pacote web).

Validação anti-stale (CI): `python scripts/verify_openapi_up_to_date.py`
ou `npm run contracts:verify` em `apps/web`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
_OUT = _REPO_ROOT / "contracts" / "openapi.json"


def main() -> int:
    try:
        from otm_api.main import app
    except ImportError as e:
        print("Falha ao importar otm_api.main — instale o pacote em modo editável.", file=sys.stderr)
        print(e, file=sys.stderr)
        return 1
    spec = app.openapi()
    _OUT.parent.mkdir(parents=True, exist_ok=True)
    _OUT.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
