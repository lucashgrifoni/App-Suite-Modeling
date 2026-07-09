"""Carregamento e consulta de mapeamentos por id de heurística → FrameworkRef.

Espelha `registry.py` (STRIDE), mas a chave é o id da heurística (ex.:
`plot4ai_prompt_injection`) em vez da categoria STRIDE. Serve a lente de IA:
liga heurísticas PLOT4ai ao OWASP LLM Top 10 (2025) e ao MITRE ATLAS, sem
alterar o schema canónico — os refs fluem pelo mesmo campo `framework_refs`.
"""

from __future__ import annotations

import importlib.resources
from collections.abc import Iterable
from functools import lru_cache
from pathlib import Path

import yaml
from otm_core_schema import FrameworkRef

from otm_framework_mappings.models import RawHeuristicMapFile, RawMappingRow


def _dedupe_refs(refs: Iterable[FrameworkRef]) -> list[FrameworkRef]:
    seen: set[tuple[str, str]] = set()
    out: list[FrameworkRef] = []
    for r in refs:
        key = (r.framework, r.control_id)
        if key in seen:
            continue  # pragma: no cover - defensive guard
        seen.add(key)
        out.append(r)
    return out


def _rows_to_refs(rows: list[RawMappingRow]) -> list[FrameworkRef]:
    refs = [FrameworkRef(framework=row.framework, control_id=row.control_id, notes=row.notes) for row in rows]
    return _dedupe_refs(refs)


class HeuristicFrameworkRegistry:
    """Registo consultável por id de heurística."""

    def __init__(self, by_heuristic: dict[str, list[FrameworkRef]]) -> None:
        self._by_heuristic = {k: list(v) for k, v in by_heuristic.items()}

    def refs_for_heuristic(self, heuristic_id: str) -> list[FrameworkRef]:
        return [FrameworkRef.model_validate(r.model_dump()) for r in self._by_heuristic.get(heuristic_id, [])]

    @classmethod
    def from_raw_file(cls, data: RawHeuristicMapFile) -> HeuristicFrameworkRegistry:
        by_heuristic = {key: _rows_to_refs(rows) for key, rows in data.by_heuristic.items()}
        return cls(by_heuristic)

    @classmethod
    def from_yaml_bytes(cls, raw: bytes) -> HeuristicFrameworkRegistry:
        obj = yaml.safe_load(raw)
        if not isinstance(obj, dict):
            raise ValueError("YAML de mapeamento deve ser um objeto na raiz.")  # pragma: no cover - defensive
        return cls.from_raw_file(RawHeuristicMapFile.model_validate(obj))

    @classmethod
    def from_yaml_path(cls, path: Path) -> HeuristicFrameworkRegistry:
        return cls.from_yaml_bytes(path.read_bytes())


def load_packaged_ai_heuristic_map() -> HeuristicFrameworkRegistry:
    """Carrega `data/ai_heuristic_framework_map.yaml` embutido no pacote."""
    pkg = importlib.resources.files("otm_framework_mappings")
    node = pkg.joinpath("data", "ai_heuristic_framework_map.yaml")
    with node.open("rb") as f:
        return HeuristicFrameworkRegistry.from_yaml_bytes(f.read())


@lru_cache(maxsize=1)
def default_ai_heuristic_registry() -> HeuristicFrameworkRegistry:
    """Instância em cache para o motor e testes."""
    return load_packaged_ai_heuristic_map()
