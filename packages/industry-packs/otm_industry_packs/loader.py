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
    if not d.is_dir():  # pragma: no cover - defensive: packaged data dir always present
        return []
    return sorted(p.stem for p in d.glob("*.yaml"))


def list_template_ids() -> list[str]:
    d = _data_dir() / "templates"
    if not d.is_dir():  # pragma: no cover - defensive: packaged data dir always present
        return []
    out: list[str] = []
    for p in d.glob("*.otm.yaml"):
        out.append(p.name.removesuffix(".otm.yaml"))
    return sorted(out)


def load_pack(pack_id: str) -> PackDefinition:
    # `pack_id` is attacker-controllable (API body / CLI flag). Accept only ids
    # that are real packs in the embedded catalog; this rejects path traversal
    # (`../`), absolute paths, and any other id before touching the filesystem,
    # so the loader can never read a YAML file outside `data/packs/`.
    known = list_pack_ids()
    if pack_id not in known:
        raise FileNotFoundError(f"Pack desconhecido: {pack_id!r} (use: {known})")
    path = _data_dir() / "packs" / f"{pack_id}.yaml"
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):  # pragma: no cover - defensive: packaged pack yaml is a valid mapping
        raise ValueError(f"Pack inválido: {path}")
    return PackDefinition.model_validate(raw)


def load_template_yaml(template_id: str) -> str:
    """Conteúdo textual do template (OTM YAML)."""
    # Same membership check as `load_pack`: only ids present in the embedded
    # catalog are read, rejecting traversal/absolute paths at the boundary.
    known = list_template_ids()
    if template_id not in known:
        raise FileNotFoundError(f"Template desconhecido: {template_id!r} (use: {known})")
    path = _data_dir() / "templates" / f"{template_id}.otm.yaml"
    return path.read_text(encoding="utf-8")


def load_template_info(template_id: str) -> TemplateInfo | None:
    """Manifest opcional `templates/<id>.meta.json`."""
    # Unknown / traversal ids resolve to "no manifest" rather than reading the
    # filesystem at an attacker-chosen path.
    if template_id not in list_template_ids():
        return None
    path = _data_dir() / "templates" / f"{template_id}.meta.json"
    if not path.is_file():
        return None  # pragma: no cover - defensive: shipped templates always have a manifest
    raw = json.loads(path.read_text(encoding="utf-8"))
    return TemplateInfo.model_validate(raw)
