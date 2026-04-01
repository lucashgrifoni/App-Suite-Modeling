"""Contratos opcionais para novos exportadores (extensibilidade sem acoplamento)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from otm_core_schema import ThreatModelDocument


@runtime_checkable
class DocumentTextExporter(Protocol):
    """Exportador que recebe só o documento canónico e devolve texto."""

    def __call__(self, doc: ThreatModelDocument) -> str: ...


@runtime_checkable
class DocumentTextExporterWithOptions(Protocol):
    """Variante com parâmetros opcionais (indent, encoding, …)."""

    def __call__(self, doc: ThreatModelDocument, **kwargs: object) -> str: ...
