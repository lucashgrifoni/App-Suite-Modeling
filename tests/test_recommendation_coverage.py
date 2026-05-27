"""Coverage — methodology recommendation scoring increments for specific contexts."""

from __future__ import annotations

from typing import Any

from otm_core_schema import ThreatModelDocument, create_blank_document
from otm_threat_engine import recommend_methodology


def _doc(system_type: str | None = None, sector: str | None = None, summary: str = "", title: str = "App") -> ThreatModelDocument:
    d: dict[str, Any] = create_blank_document().model_dump(mode="python", by_alias=True)
    m = d.setdefault("model", {})
    if system_type:
        m["system_type"] = system_type
    if sector:
        m["industry_sector"] = sector
    meta = d.setdefault("metadata", {})
    meta["title"] = title
    meta["summary"] = summary
    return ThreatModelDocument.model_validate(d)


def test_recommend_mobile_application() -> None:
    rec = recommend_methodology(_doc(system_type="mobile_application"))
    assert rec.methodology is not None


def test_recommend_cloud_native_sector() -> None:
    rec = recommend_methodology(_doc(sector="cloud_native", summary="multi-tenant bff waf api gateway"))
    assert rec.methodology is not None


def test_recommend_healthcare_sector() -> None:
    rec = recommend_methodology(_doc(sector="healthcare", summary="patient records pii"))
    assert rec.methodology is not None


def test_recommend_pasta_vulnerability_keywords() -> None:
    rec = recommend_methodology(
        _doc(summary="attack threat actor simulation vulnerability exploit enterprise advanced")
    )
    assert rec.methodology is not None


def test_recommend_cia_workshop_keywords() -> None:
    rec = recommend_methodology(_doc(summary="workshop executivo rápido para iniciante"))
    assert rec.methodology is not None


def test_recommend_ai_textual_marker() -> None:
    # AI marker in text (model/agent/inference) without explicit AI tags
    rec = recommend_methodology(_doc(title="Service", summary="model inference agent pipeline for predictions"))
    assert rec.methodology is not None
