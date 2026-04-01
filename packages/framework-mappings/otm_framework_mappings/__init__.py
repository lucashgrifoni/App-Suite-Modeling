"""
Mapeamentos funcionais OWASP, NIST, ISO, etc.

Dados versionados e consultas puras (STRIDE → `FrameworkRef`).
O enriquecimento de `HeuristicThreat` vive em `otm_threat_engine.framework_refs`
para evitar dependências circulares.
"""

from otm_framework_mappings.catalog import FrameworkCatalog, framework_display_name
from otm_framework_mappings.registry import (
    StrideFrameworkRegistry,
    default_stride_registry,
    load_packaged_stride_map,
)

__all__ = [
    "FrameworkCatalog",
    "StrideFrameworkRegistry",
    "default_stride_registry",
    "framework_display_name",
    "load_packaged_stride_map",
]
