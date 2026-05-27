"""Coverage — backlog service branches (pack, JSON/validation errors) via CLI and direct calls."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from otm_cli.application.backlog_service import run_backlog
from otm_cli.shared.enums import BacklogFormat
from otm_cli.shared.errors import CliUserError

_ROOT = Path(__file__).resolve().parents[1]
_MODEL = _ROOT / "examples" / "saas-ordering-v1.otm.yaml"


def test_backlog_from_model_with_pack() -> None:
    text = run_backlog(_MODEL, document=None, pack="saas", fmt=BacklogFormat.markdown, group_by=None)
    assert text


def test_backlog_bad_json_raises(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(CliUserError):
        run_backlog(bad, document=None, pack=None, fmt=BacklogFormat.json, group_by=None)


def test_backlog_wrong_shape_json_raises(tmp_path: Path) -> None:
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps({"unexpected": "shape"}), encoding="utf-8")
    with pytest.raises(CliUserError):
        run_backlog(wrong, document=None, pack=None, fmt=BacklogFormat.json, group_by=None)


def test_backlog_bad_pack_raises() -> None:
    with pytest.raises(CliUserError):
        run_backlog(_MODEL, document=None, pack="no_such_pack_xyz", fmt=BacklogFormat.markdown, group_by=None)
