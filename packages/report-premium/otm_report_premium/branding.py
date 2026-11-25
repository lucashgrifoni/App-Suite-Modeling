"""
Logo embarcado no PDF premium — PNG em base64 (data URI).

Resolução (ordem):
1. Variável de ambiente ``OTM_PREMIUM_LOGO_PATH`` (ficheiro absoluto).
2. ``assets/report_logo.png`` junto ao pacote (instalado via package-data).
"""

from __future__ import annotations

import base64
import logging
import os
from importlib import resources
from pathlib import Path

_LOG = logging.getLogger(__name__)

#: The data URI is labelled `image/png`, so the bytes have to actually be a PNG. Without this
#: check any other file — a JPEG, an SVG, a text file with a `.png` name — was base64-encoded
#: under a PNG label; the PDF library then printed its own `Cannot identify image file:` line
#: followed by the whole base64 blob, named neither the variable nor the file, and dropped the
#: logo. https://www.w3.org/TR/png/#5PNG-file-signature
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _logo_bytes(path: Path, *, max_bytes: int, from_env: bool) -> bytes | None:
    """PNG bytes of `path`, or None with a warning naming the reason when it cannot be used."""
    try:
        if not path.is_file():
            _reject(path, "is not a readable file", from_env=from_env)
            return None
        raw = path.read_bytes()
    except OSError as exc:  # pragma: no cover - defensive: logo file read error
        _reject(path, f"could not be read ({exc.strerror})", from_env=from_env)
        return None
    if len(raw) > max_bytes:
        _reject(path, f"is larger than the {max_bytes}-byte limit", from_env=from_env)
        return None
    if not raw.startswith(_PNG_SIGNATURE):
        _reject(path, "is not a PNG file", from_env=from_env)
        return None
    return raw


def _reject(path: Path, reason: str, *, from_env: bool) -> None:
    """Only an explicitly configured logo is worth a warning; the packaged fallback is normal."""
    if from_env:
        _LOG.warning("OTM_PREMIUM_LOGO_PATH=%s %s; using the built-in logo instead.", path, reason)


def report_logo_data_uri(*, max_bytes: int = 2_000_000) -> str | None:
    """
    Devolve ``data:image/png;base64,...`` ou None se não houver ficheiro válido.
    """
    candidates: list[tuple[Path, bool]] = []
    env = (os.environ.get("OTM_PREMIUM_LOGO_PATH") or "").strip()
    if env:
        candidates.append((Path(env).expanduser(), True))
    pkg_assets = Path(__file__).resolve().parent / "assets" / "report_logo.png"
    candidates.append((pkg_assets, False))

    for path, from_env in candidates:
        raw = _logo_bytes(path, max_bytes=max_bytes, from_env=from_env)
        if raw is not None:
            b64 = base64.standard_b64encode(raw).decode("ascii")
            return f"data:image/png;base64,{b64}"

    # Fallback: recurso empacotado (wheel/sdist)
    try:
        files = resources.files("otm_report_premium")
        logo = files.joinpath("assets", "report_logo.png")
        if logo.is_file():  # pragma: no cover - wheel-only fallback; the local asset path resolves first in-repo
            raw = logo.read_bytes()
            if len(raw) <= max_bytes:
                b64 = base64.standard_b64encode(raw).decode("ascii")
                return f"data:image/png;base64,{b64}"
    except (ModuleNotFoundError, OSError):  # pragma: no cover - defensive: packaged-resource access error
        pass

    return None
