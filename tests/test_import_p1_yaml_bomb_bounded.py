"""Artifact uploads get the same YAML alias bound as the canonical document.

The alias-expansion cap was first added only to `otm_core_schema.io`, which covers
`.otm.yaml` documents. But `otm_artifact_import` parses Terraform, Kubernetes and
OpenAPI files that arrive through `POST /v1/imports/*` — the *more* exposed surface,
since those are uploads rather than a file the operator already had. Those paths still
called bare `yaml.safe_load` / `yaml.safe_load_all`, which blocks arbitrary Python
construction but does nothing about alias expansion: a few hundred bytes can expand
into gigabytes and take the process down.
"""

from __future__ import annotations

import pytest
from otm_artifact_import._yamljson import iter_yaml_documents, load_object_from_text


def _billion_laughs(levels: int, fan_out: int = 9) -> str:
    """A tiny YAML file whose expansion is fan_out ** levels nodes."""
    lines = ["a0: &a0 lol"]
    for i in range(1, levels + 1):
        prev = f"*a{i - 1}"
        lines.append(f"a{i}: &a{i} [{', '.join([prev] * fan_out)}]")
    lines.append(f"root: *a{levels}")
    return "\n".join(lines)


def test_a_small_bomb_is_rejected_instead_of_expanded() -> None:
    text = _billion_laughs(levels=8)

    assert len(text) < 1000, "the point of the attack is that the file is tiny"
    with pytest.raises(ValueError, match="alias expansion"):
        load_object_from_text(text)


def test_multi_document_stream_shares_one_budget() -> None:
    """Per-document budgets would just mean repeating the bomb after each `---`."""
    bomb = _billion_laughs(levels=7)
    stream = "\n---\n".join([bomb] * 3)

    with pytest.raises(ValueError, match="alias expansion"):
        list(iter_yaml_documents(stream))


def test_ordinary_manifests_still_parse() -> None:
    """The bound must not get in the way of real files."""
    manifest = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: api
spec:
  replicas: 2
---
apiVersion: v1
kind: Service
metadata:
  name: api-svc
"""

    docs = list(iter_yaml_documents(manifest))

    assert [d["kind"] for d in docs] == ["Deployment", "Service"]


def test_legitimate_anchors_still_work() -> None:
    """Anchors are a normal YAML feature; only runaway expansion is the problem."""
    text = """
defaults: &defaults
  kind: process
metadata:
  name: svc
first:
  <<: *defaults
second:
  <<: *defaults
"""

    data = load_object_from_text(text)

    assert data["first"]["kind"] == "process"
    assert data["second"]["kind"] == "process"
