"""Carrega templates e packs YAML embutidos no pacote."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

import otm_industry_packs
from otm_industry_packs.models import PackDefinition, TemplateInfo


def _data_dir() -> Path:
    """Diretório `data/` junto a este pacote (funciona em editable install)."""
    return Path(otm_industry_packs.__file__).resolve().parent / "data"


def list_pack_ids() -> list[str]:
    d = _data_dir() / "packs"
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.yaml"))


def list_template_ids() -> list[str]:
    d = _data_dir() / "templates"
    if not d.is_dir():
        return []
    out: list[str] = []
    for p in d.glob("*.otm.yaml"):
        out.append(p.name.removesuffix(".otm.yaml"))
    return sorted(out)


def load_pack(pack_id: str) -> PackDefinition:
    path = _data_dir() / "packs" / f"{pack_id}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"Pack desconhecido: {pack_id!r} (use: {list_pack_ids()})")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Pack inválido: {path}")
    return PackDefinition.model_validate(raw)


def load_template_yaml(template_id: str) -> str:
    """Conteúdo textual do template (OTM YAML)."""
    path = _data_dir() / "templates" / f"{template_id}.otm.yaml"
    if not path.is_file():
        raise FileNotFoundError(
            f"Template desconhecido: {template_id!r} (use: {list_template_ids()})"
        )
    return path.read_text(encoding="utf-8")


def load_template_info(template_id: str) -> TemplateInfo | None:
    """Manifest opcional `templates/<id>.meta.json`."""
    path = _data_dir() / "templates" / f"{template_id}.meta.json"
    if not path.is_file():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    return TemplateInfo.model_validate(raw)
