"""Modelos internos para carregar YAML (não duplicam o schema canónico)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RawMappingRow(BaseModel):
    """Uma linha no YAML antes de converter para `FrameworkRef`."""

    framework: str = Field(..., min_length=1)
    control_id: str = Field(..., min_length=1)
    notes: str | None = None


class RawStrideMapFile(BaseModel):
    """Formato versionado do ficheiro principal de mapeamento STRIDE."""

    version: str = Field(default="1", description="Versão do ficheiro de dados.")
    by_stride: dict[str, list[RawMappingRow]] = Field(default_factory=dict)
    extra: dict[str, Any] = Field(
        default_factory=dict,
        description="Metadados ou extensões futuras (includes, tags, …).",
    )
