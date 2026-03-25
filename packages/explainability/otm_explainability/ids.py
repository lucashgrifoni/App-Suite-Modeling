"""Geração de IDs estáveis para `ExplanationRecord` (testável, ordenável)."""

from __future__ import annotations


def explanation_id(seq: int, *, prefix: str = "exp") -> str:
    return f"{prefix}_{seq:04d}"
