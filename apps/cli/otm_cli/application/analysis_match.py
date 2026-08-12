"""Guard: a supplied `AnalysisResult` must describe the model it is paired with.

`otm report --analysis-json`, `otm report --baseline` and `otm backlog --document` all took the
pairing on trust. Handed two artifacts from *different* systems, they produced one
authoritative-looking document titled after one and filled with the other's threats, scores and
backlog rows — exit 0, no warning.

`AnalysisResult` records the system it was produced from in `document_title`, so the mismatch is
detectable from the artifacts themselves. Entity ids are deliberately *not* used for this: the
template catalog reuses generic ids (`user`, `edge`, `app`), so two unrelated models can share
every id an analysis references, while the titles stay distinct.

This mirrors `diff-analysis`, which already refuses to gate across engine versions rather than
issuing a verdict nobody can attribute.
"""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument
from otm_threat_engine import AnalysisResult

from otm_cli.shared.errors import CliUserError


def require_analysis_matches_document(
    doc: ThreatModelDocument,
    result: AnalysisResult,
    *,
    flag: str,
) -> None:
    """Raise `CliUserError` when `result` was produced from a different system than `doc`."""
    model_title = doc.metadata.title.strip()
    analysis_title = result.document_title.strip()
    if model_title == analysis_title:
        return
    raise CliUserError(
        exit_code=1,
        failed="the supplied analysis does not describe this model.",
        cause=(
            f"`{flag}` carries an analysis of `{analysis_title}` while the model is `{model_title}`; "
            "one artifact cannot carry two systems."
        ),
        next_step=(f"drop `{flag}`, or pass an analysis produced from this model (`otm analyze <model> --json-out`)."),
    )
