"""
Logo embarcado no PDF premium — PNG em base64 (data URI).

Resolução (ordem):
1. Variável de ambiente ``OTM_PREMIUM_LOGO_PATH`` (ficheiro absoluto).
2. ``assets/report_logo.png`` junto ao pacote (instalado via package-data).
"""

from __future__ import annotations

import base64
import os
from importlib import resources
from pathlib import Path


def report_logo_data_uri(*, max_bytes: int = 2_000_000) -> str | None:
    """
    Devolve ``data:image/png;base64,...`` ou None se não houver ficheiro válido.
    """
    candidates: list[Path] = []
    env = (os.environ.get("OTM_PREMIUM_LOGO_PATH") or "").strip()
    if env:
        candidates.append(Path(env).expanduser())
    pkg_assets = Path(__file__).resolve().parent / "assets" / "report_logo.png"
    candidates.append(pkg_assets)

    for path in candidates:
        try:
            if not path.is_file():
                continue
            raw = path.read_bytes()
            if len(raw) > max_bytes:
                continue
            b64 = base64.standard_b64encode(raw).decode("ascii")
            return f"data:image/png;base64,{b64}"
        except OSError:
            continue

    # Fallback: recurso empacotado (wheel/sdist)
    try:
        files = resources.files("otm_report_premium")
        logo = files.joinpath("assets", "report_logo.png")
        if logo.is_file():
            raw = logo.read_bytes()
            if len(raw) <= max_bytes:
                b64 = base64.standard_b64encode(raw).decode("ascii")
                return f"data:image/png;base64,{b64}"
    except (ModuleNotFoundError, OSError):
        pass

    return None
