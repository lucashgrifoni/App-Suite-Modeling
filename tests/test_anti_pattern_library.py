"""Anti-pattern library: deteção conservadora por perfil semântico."""

from __future__ import annotations

from otm_core_schema import load_document_from_yaml
from otm_industry_packs.loader import load_template_yaml
from otm_threat_engine.anti_pattern_library import detect_anti_patterns


def test_api_public_profile_can_trigger_when_keywords_missing() -> None:
    raw = load_template_yaml("api-public")
    doc = load_document_from_yaml(raw)
    hits = detect_anti_patterns(doc)
    assert isinstance(hits, list)


def test_mitigating_keywords_suppress_hit() -> None:
    """`mitigating_keywords` no catálogo (ex.: CORS explícito) suprime o hit."""
    raw = """
model:
  schema_version: "1.1.0"
  methodology: stride
  template_semantic_profile: api_backend_rest
metadata:
  title: API teste CORS
  summary: Política CORS e origens restritas no gateway.
components:
  - id: user
    name: Cliente
    kind: user
    in_trust_boundary: internet
  - id: gw
    name: Gateway
    kind: gateway
    in_trust_boundary: app_tier
  - id: api
    name: API
    kind: process
    in_trust_boundary: app_tier
data_flows:
  - id: u_gw
    from_component: user
    to_component: gw
assets: []
trust_boundaries:
  - id: internet
    name: Internet
    member_component_ids: [user]
    outside_component_ids: []
    crossing_flow_ids: []
  - id: app_tier
    name: App
    member_component_ids: [gw, api]
    outside_component_ids: []
    crossing_flow_ids: []
threats: []
mitigations: []
evidence_suggestions: []
"""
    doc = load_document_from_yaml(raw)
    hits = detect_anti_patterns(doc)
    assert "ap_api_cors_policy" not in {h.id for h in hits}


def test_admin_pattern_skips_without_admin_like_component_id() -> None:
    """Gate estrutural: perfil admin sem componente `admin` no id não dispara anti-padrão admin."""
    raw = """
model:
  schema_version: "1.1.0"
  methodology: stride
  template_semantic_profile: internal_admin_portal
metadata:
  title: Falso admin
  summary: Sem componente admin no id.
components:
  - id: portal_ui
    name: UI
    kind: process
data_flows: []
assets: []
trust_boundaries: []
threats: []
mitigations: []
evidence_suggestions: []
"""
    doc = load_document_from_yaml(raw)
    hits = detect_anti_patterns(doc)
    assert "ap_admin_missing_approval_signal" not in {h.id for h in hits}


def test_import_signal_tag_enriches_corpus() -> None:
    """Tags `import:signal:` alimentam o corpus (ponte repo → anti-pattern)."""
    raw = """
model:
  schema_version: "1.1.0"
  methodology: stride
  template_semantic_profile: file_handling_application
metadata:
  title: Upload
  summary: Pipeline
  tags:
    - "import:signal:quarentena e sandbox no worker"
components:
  - id: user
    name: User
    kind: user
  - id: upload
    name: Upload
    kind: process
data_flows:
  - id: a
    from_component: user
    to_component: upload
  - id: b
    from_component: upload
    to_component: user
  - id: c
    from_component: user
    to_component: upload
assets: []
trust_boundaries: []
threats: []
mitigations: []
evidence_suggestions: []
"""
    doc = load_document_from_yaml(raw)
    hits = detect_anti_patterns(doc)
    assert "ap_upload_quarantine_gap" not in {h.id for h in hits}


def test_blank_profile_returns_no_hits() -> None:
    raw = """
model:
  schema_version: "1.1.0"
  methodology: stride
metadata:
  title: X
components: []
data_flows: []
assets: []
trust_boundaries: []
threats: []
mitigations: []
evidence_suggestions: []
"""
    doc = load_document_from_yaml(raw)
    assert detect_anti_patterns(doc) == []
