"""Limites do loader canônico contra YAML hostil (billion laughs) e ficheiros absurdos.

O ataque aqui não é o tamanho do ficheiro: `yaml.safe_load` resolve um alias partilhando o nó
de destino, por isso um ficheiro de ~600 bytes com aliases encadeados carrega-se em
milissegundos e só rebenta quando alguém serializa o documento (`otm export`). Os testes
cobrem as duas defesas em separado — o tecto de expansão e o tecto de bytes — porque um
não substitui o outro.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_core_schema.io import (
    ENV_MAX_DOCUMENT_BYTES,
    ENV_MAX_YAML_EXPANDED_NODES,
    dump_document_to_json,
    load_document_from_yaml,
    load_document_from_yaml_path,
)

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def _alias_bomb(levels: int, fan: int = 9) -> str:
    """Documento válido cujo `components[0].metadata` esconde a expansão."""
    lines = [
        "model:",
        "  schema_version: '1.1.0'",
        "metadata:",
        "  title: bomb",
        "components:",
        "  - id: c1",
        "    name: c1",
        "    kind: process",
        "    metadata:",
        "      a: &a0 x",
    ]
    for i in range(1, levels + 1):
        refs = ", ".join([f"*a{i - 1}"] * fan)
        lines.append(f"      l{i}: &a{i} [{refs}]")
    return "\n".join(lines) + "\n"


def test_alias_bomb_is_rejected_before_it_can_be_serialized() -> None:
    # 7 níveis ≈ 620 bytes de ficheiro e ~170 MB de JSON depois de `dump_document_to_json`.
    src = _alias_bomb(7)
    assert len(src) < 1024
    with pytest.raises(ValueError, match="expan"):
        load_document_from_yaml(src)


def test_recursive_alias_is_rejected() -> None:
    src = "model:\n  schema_version: '1.1.0'\nmetadata:\n  title: &r [*r]\n"
    with pytest.raises(ValueError, match="recursiv"):
        load_document_from_yaml(src)


def test_small_alias_use_still_works() -> None:
    """Aliases legítimos (reutilizar um valor) continuam a carregar e a serializar."""
    src = _alias_bomb(2)
    doc = load_document_from_yaml(src)
    assert doc.components[0].id == "c1"
    assert len(dump_document_to_json(doc)) > 0


def test_real_example_still_loads() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    assert len(doc.components) == 4


def test_expansion_limit_is_overridable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_MAX_YAML_EXPANDED_NODES, "20")
    with pytest.raises(ValueError, match="expan"):
        load_document_from_yaml_path(_MINIMAL)


@pytest.mark.parametrize("bad", ["nonsense", "0", "-1"])
def test_invalid_limit_env_is_reported_not_silently_ignored(bad: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Uma gralha no override não pode desligar o limite em silêncio."""
    monkeypatch.setenv(ENV_MAX_YAML_EXPANDED_NODES, bad)
    with pytest.raises(ValueError, match=ENV_MAX_YAML_EXPANDED_NODES):
        load_document_from_yaml("model:\n  schema_version: '1.1.0'\nmetadata:\n  title: t\n")


def test_blank_limit_env_falls_back_to_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_MAX_YAML_EXPANDED_NODES, "  ")
    assert load_document_from_yaml_path(_MINIMAL).metadata.title


def test_oversize_file_is_rejected_by_size_before_parsing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(ENV_MAX_DOCUMENT_BYTES, "128")
    big = tmp_path / "big.otm.yaml"
    big.write_text(_MINIMAL.read_text(encoding="utf-8"), encoding="utf-8")
    with pytest.raises(ValueError, match=ENV_MAX_DOCUMENT_BYTES):
        load_document_from_yaml_path(big)


def test_size_limit_does_not_touch_normal_files(tmp_path: Path) -> None:
    p = tmp_path / "ok.otm.yaml"
    p.write_text(_MINIMAL.read_text(encoding="utf-8"), encoding="utf-8")
    assert load_document_from_yaml_path(p).metadata.title
