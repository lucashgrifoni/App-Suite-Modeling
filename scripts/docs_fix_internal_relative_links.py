"""Fix relative .md links under docs/internal/ after docs reorganization."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def _sub_file(path: Path, pairs: list[tuple[str, str]]) -> None:
    text = path.read_text(encoding="utf-8")
    orig = text
    for old, new in pairs:
        text = text.replace(old, new)
    if text != orig:
        path.write_text(text, encoding="utf-8")


def main() -> None:
    cl = DOCS / "internal" / "checklists"
    cpairs = [
        ("](KNOWN_LIMITATIONS.md)", "](../../KNOWN_LIMITATIONS.md)"),
        ("](RELEASE_SCOPE_FREEZE.md)", "](../decisions/RELEASE_SCOPE_FREEZE.md)"),
        ("](ENGINEERING_CLOSEOUT_SCOPE.md)", "](../decisions/ENGINEERING_CLOSEOUT_SCOPE.md)"),
        ("](RELEASE_NOTES_v0.1.0.md)", "](../reports/RELEASE_NOTES_v0.1.0.md)"),
        ("](CI_AND_SECURITY_EVIDENCE.md)", "](../../CI_AND_SECURITY_EVIDENCE.md)"),
        ("](CONTRACTS_CI_HYBRID.md)", "](../../architecture/CONTRACTS_CI_HYBRID.md)"),
        ("](CONTRACT_AND_SNAPSHOTS.md)", "](../../features/CONTRACT_AND_SNAPSHOTS.md)"),
        ("](THREAT_MODEL_DIFF.md)", "](../../features/THREAT_MODEL_DIFF.md)"),
    ]
    for md in sorted(cl.glob("*.md")):
        _sub_file(md, cpairs)
        t = md.read_text(encoding="utf-8")
        t = t.replace("`RELEASE_SCOPE_FREEZE.md`", "`../decisions/RELEASE_SCOPE_FREEZE.md`")  # bare backticks in list items
        t = t.replace("](README.md)", "](../../README.md)")
        md.write_text(t, encoding="utf-8")

    go = cl / "GO_NO_GO_v0.1.0.md"
    if go.exists():
        t = go.read_text(encoding="utf-8")
        t = re.sub(
            r"\(\[`README\.md`\]\(\.\./README\.md\)\)",
            r"([`README.md`](../../../README.md))",
            t,
        )
        go.write_text(t, encoding="utf-8")

    dec = DOCS / "internal" / "decisions"
    dpairs = [
        ("](KNOWN_LIMITATIONS.md)", "](../../KNOWN_LIMITATIONS.md)"),
        ("](RELEASE_NOTES_v0.1.0.md)", "](../reports/RELEASE_NOTES_v0.1.0.md)"),
    ]
    for md in sorted(dec.glob("*.md")):
        _sub_file(md, dpairs)

    rep = DOCS / "internal" / "reports"
    rpairs = [
        ("](KNOWN_LIMITATIONS.md)", "](../../KNOWN_LIMITATIONS.md)"),
        ("](CI_AND_SECURITY_EVIDENCE.md)", "](../../CI_AND_SECURITY_EVIDENCE.md)"),
        ("](DEPLOYMENT_INVARIANTS.md)", "](../../architecture/DEPLOYMENT_INVARIANTS.md)"),
    ]
    for md in sorted(rep.glob("*.md")):
        _sub_file(md, rpairs)

    fe = rep / "FRONTEND_UI_ROLLOUT_HISTORY.md"
    if fe.exists():
        t = fe.read_text(encoding="utf-8")
        t = t.replace("](UI.md)", "](../../features/UI.md)")
        t = t.replace("](DESIGN_SYSTEM_FOUNDATION.md)", "](../../architecture/DESIGN_SYSTEM_FOUNDATION.md)")
        fe.write_text(t, encoding="utf-8")

    for md in (DOCS / "internal" / "logs").glob("*.md"):
        t = md.read_text(encoding="utf-8")
        t = t.replace(
            "](FINAL_GO_NO_GO_RELEASE_ASSESSMENT.md)",
            "](../reports/FINAL_GO_NO_GO_RELEASE_ASSESSMENT.md)",
        )
        md.write_text(t, encoding="utf-8")

    apairs = [
        ("](CI_AND_SECURITY_EVIDENCE.md)", "](../../CI_AND_SECURITY_EVIDENCE.md)"),
        ("](DEPLOYMENT_INVARIANTS.md)", "](../../architecture/DEPLOYMENT_INVARIANTS.md)"),
    ]
    for md in sorted((DOCS / "internal" / "audits").glob("*.md")):
        _sub_file(md, apairs)

    rc = cl / "RELEASE_CHECKLIST_RC.md"
    if rc.exists():
        t = rc.read_text(encoding="utf-8")
        t = t.replace("](CONTRACT_AND_SNAPSHOTS.md)", "](../../features/CONTRACT_AND_SNAPSHOTS.md)")
        rc.write_text(t, encoding="utf-8")

    pub = cl / "PUBLISH_PLAYBOOK.md"
    if pub.exists():
        _sub_file(
            pub,
            [
                ("](RELEASE_SCOPE_FREEZE.md)", "](../decisions/RELEASE_SCOPE_FREEZE.md)"),
                ("](KNOWN_LIMITATIONS.md)", "](../../KNOWN_LIMITATIONS.md)"),
                ("](RELEASE_NOTES_v0.1.0.md)", "](../reports/RELEASE_NOTES_v0.1.0.md)"),
            ],
        )

    pre = cl / "PREPUBLISH_CHECKLIST.md"
    if pre.exists():
        _sub_file(
            pre,
            [
                ("](RELEASE_NOTES_v0.1.0.md)", "](../reports/RELEASE_NOTES_v0.1.0.md)"),
                ("](KNOWN_LIMITATIONS.md)", "](../../KNOWN_LIMITATIONS.md)"),
            ],
        )

    print("docs_fix_internal_relative_links: done")


if __name__ == "__main__":
    main()
