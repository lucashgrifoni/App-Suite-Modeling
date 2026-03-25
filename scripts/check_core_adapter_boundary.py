#!/usr/bin/env python3
"""
Verifica que pacotes de domínio (core-schema, threat-engine) não importam
frameworks de adaptador (FastAPI, Typer, Starlette, Uvicorn).

Uso (na raiz do repositório):
    python scripts/check_core_adapter_boundary.py

Saída: código 0 se OK; 1 se encontrar imports proibidos; mensagens em stderr.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PACKAGES = (
    ROOT / "packages" / "core-schema" / "otm_core_schema",
    ROOT / "packages" / "threat-engine" / "otm_threat_engine",
)

_FORBIDDEN_IMPORT = re.compile(
    r"^\s*(?:from|import)\s+(fastapi|typer|starlette|uvicorn)\b",
    re.IGNORECASE,
)


def main() -> int:
    violations: list[str] = []
    for base in PACKAGES:
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*.py")):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError as e:
                violations.append(f"{path.relative_to(ROOT)}: read error {e}")
                continue
            for i, line in enumerate(text.splitlines(), start=1):
                if _FORBIDDEN_IMPORT.match(line):
                    violations.append(f"{path.relative_to(ROOT)}:{i}: {line.strip()}")

    if violations:
        print("Imports de adaptador não permitidos no core/motor:\n", file=sys.stderr)
        for v in violations:
            print(f"  {v}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
