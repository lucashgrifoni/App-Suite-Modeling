"""
Templates e industry packs (YAML declarativos).

- **Templates:** esqueletos `.otm.yaml` para `otm init -t`.
- **Packs:** ajustes de risco + ameaças de contexto; usados em `analyze --pack`.
"""

from otm_industry_packs.loader import (
    list_pack_ids,
    list_template_ids,
    load_pack,
    load_template_yaml,
)
from otm_industry_packs.models import PackDefinition, TemplateInfo

__all__ = [
    "PackDefinition",
    "TemplateInfo",
    "list_pack_ids",
    "list_template_ids",
    "load_pack",
    "load_template_yaml",
]
