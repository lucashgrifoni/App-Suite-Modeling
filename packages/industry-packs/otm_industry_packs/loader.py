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
def _pack_ids() -> tuple[str, ...]:
    d = _data_dir() / "packs"
    if not d.is_dir():  # pragma: no cover - defensive: packaged data dir always present
        return ()
    return tuple(sorted(p.stem for p in d.glob("*.yaml")))


@lru_cache(maxsize=1)
def _template_ids() -> tuple[str, ...]:
    """O catálogo embutido, lido do disco uma vez por processo.

    `load_all_template_infos` enumera o catálogo e depois chama `load_template_info` por template,
    que volta a enumerá-lo para validar o id que acabou de receber: com 38 templates embarcados,
    **39 globs** por pedido. Medido contra uvicorn real, `GET /v1/templates` era a rota mais lenta
    da API — p50 43,5 ms, contra 20,7 ms de `POST /v1/models/analyze`, que corre o motor STRIDE
    inteiro. Servir um catálogo estático custava mais do que analisar um modelo de ameaças.

    Isto é dado de pacote: não muda enquanto o processo vive. É o mesmo tratamento que os registos
    de framework já recebem neste repositório.

    O resultado é uma tupla, e quem chama recebe sempre uma `list` nova construída a partir dela —
    entregar a própria lista da cache deixaria um chamador corromper todos os seguintes.
    """
    d = _data_dir() / "templates"
    if not d.is_dir():  # pragma: no cover - defensive: packaged data dir always present
        return ()
    return tuple(sorted(p.name.removesuffix(".otm.yaml") for p in d.glob("*.otm.yaml")))


def list_pack_ids() -> list[str]:
    return list(_pack_ids())


def list_template_ids() -> list[str]:
    return list(_template_ids())


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
