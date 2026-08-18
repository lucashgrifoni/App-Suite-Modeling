"""P3 regression — the engine must not raise a finding and then delete the fix for it.

`filter_pack_control_hints` is a lexical domain filter for *industry pack* hints, which packs
emit unconditionally: it drops a hint about payments, admin access or file uploads when nothing
in the model anchors it. Organisation rules loaded with `--rules` are the opposite case —
`collect_control_hints` returns the control of a rule only when that rule actually **fired**, so
the anchor question has already been answered by the match itself.

The engine merged the two lists and passed both through the filter. A rule that matched
`privilege_level: admin` or `supports_file_upload: true` had its control silently discarded,
because those are structured fields and the filter's corpus read only free text. The threat was
raised, the fix was thrown away, and nothing in the `AnalysisResult` said so — the omission is
indistinguishable from a control the rule author never wrote.

Two things are pinned here: fired-rule controls bypass the filter entirely, and the filter's own
corpus now sees structure as well as prose, so it stops mis-firing on pack hints for the same
reason. The last two tests hold the other direction — an off-domain hint is still dropped.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from otm_core_schema import ThreatModelDocument
from otm_threat_engine import analyze_document
from otm_threat_engine.custom_rules.loader import load_custom_rules
from otm_threat_engine.recommendation_gate import filter_pack_control_hints

_ADMIN_HINT = "Quarterly admin access review with a named accountable owner"
_UPLOAD_HINT = "Scan every file upload and reject executable content"
_ENCRYPTION_HINT = "Encryption at rest with the platform key hierarchy"

#: No component, asset, title or description carries the words "admin" or "upload". The model
#: says what it is in structured fields only — which is what the schema is for.
_STRUCTURED_MODEL: dict[str, Any] = {
    "model": {"schema_version": "1.0.0", "system_type": "web_application"},
    "metadata": {"title": "Portal de documentos", "owner": "appsec@empresa.example"},
    "trust_boundaries": [
        {"id": "internet", "name": "Internet", "member_component_ids": ["client"]},
        {"id": "vpc", "name": "VPC", "member_component_ids": ["edge", "vault"]},
    ],
    "components": [
        {"id": "client", "name": "Cliente", "kind": "user"},
        {
            "id": "edge",
            "name": "Servico de borda",
            "kind": "process",
            "privilege_level": "admin",
            "supports_admin_operations": True,
        },
        {"id": "vault", "name": "Cofre", "kind": "datastore"},
    ],
    "data_flows": [
        {
            "id": "submit_doc",
            "name": "Envio",
            "from_component": "client",
            "to_component": "edge",
            "protocol": "https",
            "supports_file_upload": True,
            "auth_required": False,
        }
    ],
    "assets": [],
    "threats": [],
}

_RULES: dict[str, Any] = {
    "id": "acme",
    "rules": [
        {
            "id": "privileged_component_review",
            "title": "Privileged component needs an access review",
            "stride": "elevation_of_privilege",
            "control_hint": _ADMIN_HINT,
            "match": {"component": {"privilege_level": "admin"}},
        },
        {
            "id": "upload_without_auth",
            "title": "File upload reachable without authentication",
            "stride": "tampering",
            "control_hint": _UPLOAD_HINT,
            "match": {"flow": {"supports_file_upload": True, "auth_required": False}},
        },
        {
            "id": "datastore_encryption",
            "title": "Datastore must use approved encryption at rest",
            "stride": "information_disclosure",
            "control_hint": _ENCRYPTION_HINT,
            "match": {"component": {"kind": "datastore"}},
        },
    ],
}


@pytest.fixture
def structured_doc() -> ThreatModelDocument:
    return ThreatModelDocument.model_validate(_STRUCTURED_MODEL)


@pytest.fixture
def rules_path(tmp_path: Path) -> Path:
    path = tmp_path / "acme.rules.yaml"
    path.write_text(yaml.safe_dump(_RULES, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


# ------------------------------------- a fired rule keeps the control it came with


def test_every_fired_rule_keeps_its_control_hint(structured_doc: ThreatModelDocument, rules_path: Path) -> None:
    result = analyze_document(structured_doc, custom_rules=load_custom_rules(rules_path))

    assert result.pack_control_hints == [_ADMIN_HINT, _UPLOAD_HINT, _ENCRYPTION_HINT]


def test_the_threats_and_their_controls_arrive_together(structured_doc: ThreatModelDocument, rules_path: Path) -> None:
    """The defect was raising the finding and dropping the fix; both must be present."""
    result = analyze_document(structured_doc, custom_rules=load_custom_rules(rules_path))
    raised = {h.id for h in result.heuristic_threats if h.id.startswith("custom_")}

    assert "custom_acme_privileged_component_review_edge" in raised
    assert _ADMIN_HINT in result.pack_control_hints
    assert "custom_acme_upload_without_auth_submit_doc" in raised
    assert _UPLOAD_HINT in result.pack_control_hints


def test_a_rule_that_never_fired_still_contributes_no_control(tmp_path: Path) -> None:
    """`collect_control_hints` is what makes the filter unnecessary — it must keep holding."""
    payload = {
        "id": "acme",
        "rules": [
            {
                "id": "queue_hardening",
                "title": "Queues need a dead-letter policy",
                "stride": "denial_of_service",
                "control_hint": "Dead-letter queue with an alert on depth",
                "match": {"component": {"kind": "queue"}},
            }
        ],
    }
    path = tmp_path / "unfired.rules.yaml"
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")

    result = analyze_document(
        ThreatModelDocument.model_validate(_STRUCTURED_MODEL), custom_rules=load_custom_rules(path)
    )

    assert result.pack_control_hints == []


# --------------------- the pack filter reads structure as well as prose


def test_a_structurally_declared_model_anchors_pack_hints(structured_doc: ThreatModelDocument) -> None:
    kept = filter_pack_control_hints(structured_doc, [_ADMIN_HINT, _UPLOAD_HINT])

    assert kept == [_ADMIN_HINT, _UPLOAD_HINT]


def test_a_model_without_those_signals_still_drops_the_same_hints() -> None:
    """The control: without the structured flags the hints have no anchor and must go."""
    plain = ThreatModelDocument.model_validate(
        {
            **_STRUCTURED_MODEL,
            "components": [
                {"id": "client", "name": "Cliente", "kind": "user"},
                {"id": "edge", "name": "Servico de borda", "kind": "process"},
                {"id": "vault", "name": "Cofre", "kind": "datastore"},
            ],
            "data_flows": [
                {
                    "id": "submit_doc",
                    "name": "Envio",
                    "from_component": "client",
                    "to_component": "edge",
                    "protocol": "https",
                }
            ],
        }
    )

    assert filter_pack_control_hints(plain, [_ADMIN_HINT, _UPLOAD_HINT]) == []


def test_an_off_domain_pack_hint_is_still_filtered(structured_doc: ThreatModelDocument) -> None:
    """This model has no payment surface at all; the filter must still say so."""
    payment_hint = "Reconcile every payment against the PSP ledger before fulfilment"

    assert filter_pack_control_hints(structured_doc, [payment_hint]) == []
