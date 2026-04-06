"""Write files and JSON payloads (no Rich/Typer)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_json_file(*, payload: dict[str, Any], output: Path) -> None:
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
