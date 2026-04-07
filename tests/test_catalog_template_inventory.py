"""Inventário embutido: contagem de templates em disco vs metadados."""

from __future__ import annotations

from pathlib import Path

import otm_industry_packs
from otm_industry_packs.catalog.registry_data import EXPANSION_TEMPLATE_SPECS
from otm_industry_packs.loader import list_template_ids, load_template_info


def test_shipped_template_yaml_count_is_38() -> None:
    data = Path(otm_industry_packs.__file__).resolve().parent / "data" / "templates"
    yamls = list(data.glob("*.otm.yaml"))
    assert len(yamls) == 38


def test_every_template_has_meta_json() -> None:
    data = Path(otm_industry_packs.__file__).resolve().parent / "data" / "templates"
    for tid in list_template_ids():
        assert (data / f"{tid}.meta.json").is_file(), f"missing meta for {tid}"


def test_expansion_specs_reasonable_vs_disk() -> None:
    """Lista de expansão menor ou igual ao inventário em disco (emit parcial)."""
    ids_on_disk = set(list_template_ids())
    ids_expansion = {spec.meta["id"] for spec in EXPANSION_TEMPLATE_SPECS}
    assert ids_expansion.issubset(ids_on_disk)


def test_core_templates_suggested_pack_not_forced_to_saas_for_identity_ai() -> None:
    for tid in ("admin-portal", "identity-sso", "ai-llm-chat", "industry-healthcare-clinical"):
        info = load_template_info(tid)
        assert info is not None
        assert info.suggested_pack != "saas", tid
