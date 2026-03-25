"""Carregamento e consulta de mapeamentos STRIDE → FrameworkRef."""

from __future__ import annotations

import importlib.resources
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

import yaml
from otm_core_schema import FrameworkRef, StrideCategory

from otm_framework_mappings.models import RawStrideMapFile


def _dedupe_refs(refs: Iterable[FrameworkRef]) -> list[FrameworkRef]:
    seen: set[tuple[str, str]] = set()
    out: list[FrameworkRef] = []
    for r in refs:
        key = (r.framework, r.control_id)
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _rows_to_refs(rows: list) -> list[FrameworkRef]:
    refs: list[FrameworkRef] = []
    for row in rows:
        refs.append(
            FrameworkRef(
                framework=row.framework,
                control_id=row.control_id,
                notes=row.notes,
            )
        )
    return _dedupe_refs(refs)


class StrideFrameworkRegistry:
    """
    Registo consultável por categoria STRIDE.

    Futuro: carregar vários ficheiros (`includes` no YAML ou API `merge_registry`).
    """

    def __init__(self, by_stride: dict[str, list[FrameworkRef]]) -> None:
        self._by_stride = {k: list(v) for k, v in by_stride.items()}

    def refs_for_stride(self, stride: StrideCategory) -> list[FrameworkRef]:
        key = stride.value
        return [FrameworkRef.model_validate(r.model_dump()) for r in self._by_stride.get(key, [])]

    @classmethod
    def from_raw_file(cls, data: RawStrideMapFile) -> StrideFrameworkRegistry:
        by_stride: dict[str, list[FrameworkRef]] = {}
        for stride_key, rows in data.by_stride.items():
            by_stride[stride_key] = _rows_to_refs(rows)
        return cls(by_stride)

    @classmethod
    def from_yaml_bytes(cls, raw: bytes) -> StrideFrameworkRegistry:
        obj = yaml.safe_load(raw)
        if not isinstance(obj, dict):
            raise ValueError("YAML de mapeamento deve ser um objeto na raiz.")
        parsed = RawStrideMapFile.model_validate(obj)
        return cls.from_raw_file(parsed)

    @classmethod
    def from_yaml_path(cls, path: Path) -> StrideFrameworkRegistry:
        return cls.from_yaml_bytes(path.read_bytes())


def load_packaged_stride_map() -> StrideFrameworkRegistry:
    """Carrega `data/stride_framework_map.yaml` embutido no pacote."""
    pkg = importlib.resources.files("otm_framework_mappings")
    node = pkg.joinpath("data", "stride_framework_map.yaml")
    with node.open("rb") as f:
        return StrideFrameworkRegistry.from_yaml_bytes(f.read())


@lru_cache(maxsize=1)
def default_stride_registry() -> StrideFrameworkRegistry:
    """Instância em cache para o motor e testes."""
    return load_packaged_stride_map()
