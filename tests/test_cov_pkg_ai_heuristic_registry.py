"""Loading the AI-lens heuristic map from a path on disk.

The shipped map is read from package data via `from_yaml_bytes`; `from_yaml_path` is the
classmethod that lets an operator point at their own file. Its STRIDE sibling
(`StrideFrameworkRegistry.from_yaml_path`) has a test and this one did not, so a regression in
the path variant would only surface for whoever tried to override the map.
"""

from __future__ import annotations

from pathlib import Path

import otm_framework_mappings
import pytest
from otm_framework_mappings.ai_heuristic_registry import (
    HeuristicFrameworkRegistry,
    default_ai_heuristic_registry,
)

_PACKAGED_MAP = Path(otm_framework_mappings.__file__).resolve().parent / "data" / "ai_heuristic_framework_map.yaml"

_OVERRIDE = """
version: "1"
by_heuristic:
  plot4ai_prompt_injection:
    - framework: owasp_llm
      control_id: "LLM01:2025"
      notes: "local override"
"""


def test_loading_the_packaged_map_by_path_matches_loading_it_from_package_data() -> None:
    from_path = HeuristicFrameworkRegistry.from_yaml_path(_PACKAGED_MAP)
    packaged = default_ai_heuristic_registry()

    from_path_refs = from_path.refs_for_heuristic("plot4ai_prompt_injection")
    packaged_refs = packaged.refs_for_heuristic("plot4ai_prompt_injection")

    assert from_path_refs, "the packaged map must map the prompt-injection heuristic"
    assert [r.control_id for r in from_path_refs] == [r.control_id for r in packaged_refs]


def test_an_operator_supplied_map_is_read_from_the_given_path(tmp_path: Path) -> None:
    override = tmp_path / "ai_map.yaml"
    override.write_text(_OVERRIDE, encoding="utf-8")

    refs = HeuristicFrameworkRegistry.from_yaml_path(override).refs_for_heuristic("plot4ai_prompt_injection")

    assert [r.control_id for r in refs] == ["LLM01:2025"]
    assert refs[0].notes == "local override"


def test_an_unmapped_heuristic_yields_no_refs(tmp_path: Path) -> None:
    override = tmp_path / "ai_map.yaml"
    override.write_text(_OVERRIDE, encoding="utf-8")

    assert HeuristicFrameworkRegistry.from_yaml_path(override).refs_for_heuristic("not_in_the_map") == []


def test_a_missing_map_file_raises_rather_than_loading_an_empty_registry(tmp_path: Path) -> None:
    """Silently returning an empty registry would drop every AI reference from the report."""
    with pytest.raises(FileNotFoundError, match="absent"):
        HeuristicFrameworkRegistry.from_yaml_path(tmp_path / "absent.yaml")
