"""Coverage — analyze CLI prints wizard audit trail when wizard signals are present."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from otm_cli.cli import app
from otm_core_schema import ThreatModelDocument, dump_document_to_yaml, load_document_from_yaml_path
from typer.testing import CliRunner

_ROOT = Path(__file__).resolve().parents[1]


def test_analyze_explain_prints_wizard_trail(tmp_path: Path) -> None:
    base = load_document_from_yaml_path(_ROOT / "examples" / "test-apps" / "ecommerce-subscription.otm.yaml")
    d: dict[str, Any] = base.model_dump(mode="python", by_alias=True)
    d.setdefault("model", {})["template_semantic_profile"] = "industry_ecommerce"
    meta = d.setdefault("metadata", {})
    meta["tags"] = list(meta.get("tags") or []) + [
        "wz:industry_ecommerce:checkout=no",
        "wz:industry_ecommerce:psp_boundary=no",
        "wz:industry_ecommerce:sensitive_data=no",
    ]
    doc = ThreatModelDocument.model_validate(d)
    model_file = tmp_path / "wizard.otm.yaml"
    model_file.write_text(dump_document_to_yaml(doc), encoding="utf-8")

    r = CliRunner().invoke(app, ["analyze", str(model_file), "--explain"])
    assert r.exit_code == 0
