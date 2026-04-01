"""Garante que o script de fronteira core/adaptador continua a passar no repositório."""

from __future__ import annotations

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "check_core_adapter_boundary.py"


def test_core_adapter_boundary_script_passes() -> None:
    spec = importlib.util.spec_from_file_location("check_core_adapter_boundary", _SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main() == 0
