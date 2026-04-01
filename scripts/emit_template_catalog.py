"""
Emite ficheiros `*.otm.yaml` e `*.meta.json` a partir de `registry_data.EXPANSION_TEMPLATE_SPECS`.

Uso (na raiz do repositório, com PYTHONPATH dos pacotes):
  python scripts/emit_template_catalog.py

Requer pacote `otm_industry_packs` importável (ex.: `pip install -e .` ou pytest pythonpath).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

# Permite execução sem editable install quando pythonpath inclui packages/
_REPO = Path(__file__).resolve().parents[1]
for _p in ("packages/core-schema", "packages/industry-packs"):
    _abs = str(_REPO / _p)
    if _abs not in sys.path:
        sys.path.insert(0, _abs)

from otm_core_schema import load_document_from_dict  # noqa: E402
from otm_industry_packs.catalog.registry_data import EXPANSION_TEMPLATE_SPECS  # noqa: E402


def main() -> None:
    tpl_dir = _REPO / "packages" / "industry-packs" / "otm_industry_packs" / "data" / "templates"
    tpl_dir.mkdir(parents=True, exist_ok=True)
    for spec in EXPANSION_TEMPLATE_SPECS:
        tid = spec.meta["id"]
        yaml_path = tpl_dir / f"{tid}.otm.yaml"
        meta_path = tpl_dir / f"{tid}.meta.json"
        yaml_path.write_text(
            yaml.dump(
                spec.otm,
                allow_unicode=True,
                sort_keys=False,
                default_flow_style=False,
            ),
            encoding="utf-8",
        )
        meta_path.write_text(json.dumps(spec.meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        load_document_from_dict(spec.otm)
    print(f"Emitidos {len(EXPANSION_TEMPLATE_SPECS)} templates em {tpl_dir}")


if __name__ == "__main__":
    main()
