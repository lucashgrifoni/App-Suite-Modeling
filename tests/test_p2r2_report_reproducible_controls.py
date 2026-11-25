"""The premium report has to be byte-identical across runs, workers and hash seeds.

Round 1 reported non-reproducible premium reports and this instance survived it: ten identical
`otm report … -l deep` runs produced two distinct hashes, differing on exactly one line —
`- **Controlos:** data_protection, hardening_and_integrity` versus the reverse — and four
independent uvicorn workers answering the identical `POST /v1/reports/premium` returned two
distinct bodies. `PYTHONHASHSEED=0` made all runs identical, which pinned it on set iteration
rather than on a timestamp.

`builder.py` built each root-cause group's control list as `list({...})[:6]`. Reproduced at
source: on `examples/saas-ordering-v1.otm.yaml` that expression yields
`['data_protection', 'hardening_and_integrity']` under seeds 0, 1 and 3 and the reverse under
seed 2. Beyond the churn in a committed artifact and the random failure of any hash-based
evidence check, the `[:6]` slice meant a group with more than six distinct control types would
have *dropped a different control* on each run.

`suggested_controls` is on the payload, so the instability reached the Markdown report, the API
response and the PDF alike.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

import pytest
from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from otm_report_premium import build_premium_report_payload
from otm_report_premium.builder import _build_root_cause_groups
from otm_report_premium.enums import ReportLevel
from otm_report_premium.render_markdown import render_premium_markdown
from otm_threat_engine import analyze_document, build_remediation_backlog

_ROOT = Path(__file__).resolve().parents[1]
_MODEL = _ROOT / "examples" / "saas-ordering-v1.otm.yaml"

_DIGEST_SNIPPET = (
    "import hashlib;"
    "from otm_core_schema import load_document_from_yaml_path;"
    "from otm_threat_engine import analyze_document;"
    "from otm_report_premium import build_premium_report_payload;"
    "from otm_report_premium.enums import ReportLevel;"
    "from otm_report_premium.render_markdown import render_premium_markdown;"
    "d=load_document_from_yaml_path('examples/saas-ordering-v1.otm.yaml');"
    "r=analyze_document(d);"
    "print(hashlib.sha256(''.join("
    "render_premium_markdown(build_premium_report_payload(d, r, level=level))"
    " for level in (ReportLevel.STANDARD, ReportLevel.DEEP)).encode()).hexdigest())"
)


def _digest_under_seed(seed: int) -> str:
    env = {**os.environ, "PYTHONHASHSEED": str(seed), "PYTHONIOENCODING": "utf-8"}
    proc = subprocess.run(
        [sys.executable, "-c", _DIGEST_SNIPPET],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(_ROOT),
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip().splitlines()[-1]


@pytest.fixture
def document() -> ThreatModelDocument:
    return load_document_from_yaml_path(_MODEL)


def _markdown_digest(document: ThreatModelDocument, level: ReportLevel) -> str:
    payload = build_premium_report_payload(document, analyze_document(document), level=level)
    return hashlib.sha256(render_premium_markdown(payload).encode("utf-8")).hexdigest()


@pytest.mark.parametrize("level", [ReportLevel.STANDARD, ReportLevel.DEEP])
def test_two_builds_of_the_same_model_agree(document: ThreatModelDocument, level: ReportLevel) -> None:
    """Same process, so this only catches instability that does not need a second hash seed."""
    assert _markdown_digest(document, level) == _markdown_digest(document, level)


def test_the_report_bytes_do_not_depend_on_the_hash_seed() -> None:
    """The real regression test: seed 2 was the one that flipped the control order."""
    baseline = _digest_under_seed(0)

    assert [_digest_under_seed(seed) for seed in (1, 2, 3, 42)] == [baseline] * 4


def test_the_control_list_follows_the_backlog_order(document: ThreatModelDocument) -> None:
    """The fix deduplicates in order rather than sorting: the six kept controls are the first
    six the backlog offers, in that order."""
    backlog = build_remediation_backlog(analyze_document(document), document)
    groups = _build_root_cause_groups(backlog, "pt-BR")
    group = next(g for g in groups if len(g.suggested_controls) > 1)
    items = [i for i in backlog.items if i.id in backlog.by_root_cause[group.key]]
    expected = list(dict.fromkeys(item.suggested_control_type for item in items))[:6]

    assert group.suggested_controls == expected


def test_the_control_list_is_deduplicated(document: ThreatModelDocument) -> None:
    backlog = build_remediation_backlog(analyze_document(document), document)
    groups = _build_root_cause_groups(backlog, "pt-BR")
    duplicated = [g.key for g in groups if len(set(g.suggested_controls)) != len(g.suggested_controls)]

    assert duplicated == []


def test_the_control_list_never_exceeds_six(document: ThreatModelDocument) -> None:
    """The `[:6]` slice is what made a set here dangerous rather than merely untidy."""
    backlog = build_remediation_backlog(analyze_document(document), document)
    oversized = [g.key for g in _build_root_cause_groups(backlog, "pt-BR") if len(g.suggested_controls) > 6]

    assert oversized == []


def test_the_seed_probe_actually_produced_a_digest() -> None:
    """Guards the seed comparison from passing on an empty string if the snippet stops printing."""
    assert len(_digest_under_seed(7)) == 64
