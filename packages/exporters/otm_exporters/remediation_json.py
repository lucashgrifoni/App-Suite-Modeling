"""Serialização JSON do backlog de remediação."""

from __future__ import annotations

import json

from otm_threat_engine.remediation import RemediationBacklog


def export_remediation_backlog_json(backlog: RemediationBacklog, *, indent: int = 2) -> str:
    return json.dumps(backlog.model_dump(mode="json"), indent=indent, ensure_ascii=False)


def export_remediation_backlog_obj(backlog: RemediationBacklog) -> dict:
    return backlog.model_dump(mode="json")
