"""Carrega templates e packs YAML embutidos no pacote."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import yaml

import otm_industry_packs
from otm_industry_packs.models import PackDefinition, TemplateInfo


def _data_dir() -> Path:
    """Diretório `data/` junto a este pacote (funciona em editable install)."""
    return Path(otm_industry_packs.__file__).resolve().parent / "data"


@lru_cache(maxsize=1)
def _pack_paths() -> dict[str, Path]:
    directory = _data_dir() / "packs"
    return {path.stem: path for path in directory.glob("*.yaml")}


@lru_cache(maxsize=1)
def _template_paths() -> dict[str, Path]:
    """Guarda o catálogo embutido em cache durante a vida do processo."""
    directory = _data_dir() / "templates"
    return {path.name.removesuffix(".otm.yaml"): path for path in directory.glob("*.otm.yaml")}


def list_pack_ids() -> list[str]:
    return sorted(_pack_paths())


def list_template_ids() -> list[str]:
    return sorted(_template_paths())


def load_pack(pack_id: str) -> PackDefinition:
    path = _pack_paths().get(pack_id)
    if path is None:
        raise FileNotFoundError(f"Pack desconhecido: {pack_id!r} (use: {list_pack_ids()})")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):  # pragma: no cover - defensive: packaged pack yaml is a valid mapping
        raise ValueError(f"Pack inválido: {path}")
    return PackDefinition.model_validate(raw)


def load_template_yaml(template_id: str) -> str:
    """Conteúdo textual do template (OTM YAML)."""
    path = _template_paths().get(template_id)
    if path is None:
        raise FileNotFoundError(f"Template desconhecido: {template_id!r} (use: {list_template_ids()})")
    return path.read_text(encoding="utf-8")


def load_template_info(template_id: str) -> TemplateInfo | None:
    """Manifest opcional `templates/<id>.meta.json`."""
    template_path = _template_paths().get(template_id)
    if template_path is None:
        return None
    path = template_path.with_name(f"{template_path.name.removesuffix('.otm.yaml')}.meta.json")
    if not path.is_file():
        return None  # pragma: no cover - defensive: shipped templates always have a manifest
    raw = json.loads(path.read_text(encoding="utf-8"))
    return TemplateInfo.model_validate(raw)
