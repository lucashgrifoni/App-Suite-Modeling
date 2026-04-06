"""Testes unitários da camada `application` da CLI (sem invocar Typer)."""

from __future__ import annotations

from pathlib import Path

import pytest
from otm_cli.application.analyze_service import run_analyze
from otm_cli.application.export_service import run_export
from otm_cli.application.validate_service import run_validate
from otm_cli.shared.enums import ExportFormat
from otm_cli.shared.errors import CliUserError
from otm_core_schema import load_document_from_yaml_path
from otm_threat_engine import analyze_document

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"


def test_validate_service_ok() -> None:
    doc = run_validate(_MINIMAL)
    assert doc.metadata.title


def test_validate_service_missing_file() -> None:
    with pytest.raises(CliUserError) as ei:
        run_validate(Path("nope_missing_file_12345.otm.yaml"))
    assert ei.value.exit_code == 1


def test_export_service_json_contains_title() -> None:
    text = run_export(_MINIMAL, export_format=ExportFormat.json)
    assert '"title"' in text


def test_analyze_service_returns_result() -> None:
    result = run_analyze(_MINIMAL, pack=None, methodology=None, auto_methodology=False)
    assert result.document_title
    assert result.summary is not None


def test_analyze_matches_direct_engine() -> None:
    doc = load_document_from_yaml_path(_MINIMAL)
    expected = analyze_document(doc)
    got = run_analyze(_MINIMAL, pack=None, methodology=None, auto_methodology=False)
    assert got.document_title == expected.document_title
    assert got.engine_version == expected.engine_version
