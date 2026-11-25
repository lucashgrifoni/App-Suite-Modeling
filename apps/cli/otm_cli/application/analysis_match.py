"""Guards: a supplied `AnalysisResult` must belong with the artifact it is paired with.

`otm report --analysis-json`, `otm report --baseline` and `otm backlog --document` all took the
pairing on trust. Handed two artifacts from *different* systems, they produced one
authoritative-looking document titled after one and filled with the other's threats, scores and
backlog rows — exit 0, no warning.

The first fix compared `document_title`, and that signal fails in both directions:

* it is not distinguishing — `otm init -t <template>` copies the template's title verbatim, so
  two unrelated models built from templates collide on it and cross-paired silently;
* it is not stable — renaming a model between releases made `--baseline` refuse the exact pair
  the flag exists for, and the refusal replaced the whole report;
* it is not fresh — an analysis of an earlier revision of the *same* document carries the same
  title, so the report inventoried components it then reported no threat against.

Identity now comes from `otm_threat_engine.analysis_identity`, shared with the API guard and with
`diff-analysis` so the surfaces cannot drift apart again. Two relations, deliberately different:

* `require_analysis_matches_document` — same *revision*, for `--analysis-json` and `--document`;
* `require_baseline_describes_same_system` — same *system* across revisions, for `--baseline`.
"""

from __future__ import annotations

from otm_core_schema import ThreatModelDocument
from otm_threat_engine import AnalysisResult
from otm_threat_engine.analysis_identity import (
    foreign_entity_ids,
    system_overlap,
    unanalysed_component_ids,
)

from otm_cli.shared.errors import CliUserError

#: Enough evidence to act on without pasting a 400-entity model into a terminal.
_MAX_LISTED = 6

_NOT_THIS_MODEL = "the supplied analysis does not describe this model."


def _listed(entity_ids: list[str]) -> str:
    shown = ", ".join(entity_ids[:_MAX_LISTED])
    if len(entity_ids) <= _MAX_LISTED:
        return shown
    return f"{shown} (+{len(entity_ids) - _MAX_LISTED} more)"


def _re_pair(flag: str) -> str:
    return f"drop `{flag}`, or pass an analysis produced from this model (`otm analyze <model> --json-out`)."


def require_analysis_matches_document(
    doc: ThreatModelDocument,
    result: AnalysisResult,
    *,
    flag: str,
) -> None:
    """Raise `CliUserError` when `result` was not produced from *this revision* of `doc`."""
    foreign = foreign_entity_ids(doc, result)
    if foreign:
        raise CliUserError(
            exit_code=1,
            failed=_NOT_THIS_MODEL,
            cause=(
                f"`{flag}` carries an analysis of `{result.document_title.strip()}`, which hangs threats "
                f"off entities this model does not define: {_listed(foreign)}; one artifact cannot carry "
                "two systems."
            ),
            next_step=_re_pair(flag),
        )

    unanalysed = unanalysed_component_ids(doc, result)
    if unanalysed:
        raise CliUserError(
            exit_code=1,
            failed="the supplied analysis is older than this model.",
            cause=(
                f"`{flag}` carries an analysis that never saw {len(unanalysed)} component(s) this model "
                f"defines: {_listed(unanalysed)}; the artifact would list them and carry no finding "
                "against them."
            ),
            next_step=f"re-run `otm analyze <model> --json-out` for this revision, or drop `{flag}`.",
        )

    model_title = doc.metadata.title.strip()
    analysis_title = result.document_title.strip()
    if model_title == analysis_title:
        return
    raise CliUserError(
        exit_code=1,
        failed=_NOT_THIS_MODEL,
        cause=(
            f"`{flag}` carries an analysis of `{analysis_title}` while the model is `{model_title}`; "
            "one artifact cannot carry two systems."
        ),
        next_step=_re_pair(flag),
    )


def require_baseline_describes_same_system(
    current: AnalysisResult,
    baseline: AnalysisResult,
    *,
    flag: str,
) -> None:
    """Raise `CliUserError` when `baseline` is not an earlier version of the same system.

    A baseline is *by definition* an analysis of another revision, so nothing here may demand
    that the two agree: not the title (renaming between releases is ordinary, and refusing cost
    the user the entire report), not the component set (adding components is the change a
    baseline exists to show). Only a wholesale change of system is refused, on the same measure
    `diff-analysis` gates on.
    """
    overlap = system_overlap(baseline, current)
    if overlap.is_same_system:
        return
    raise CliUserError(
        exit_code=1,
        failed="the supplied baseline does not describe this system.",
        cause=(
            f"`{flag}` carries an analysis of `{baseline.document_title.strip()}`, sharing "
            f"{overlap.shared} of the {overlap.smaller} structural entities the smaller side models; "
            "a baseline is an earlier version of the same system, so the diff would be invented."
        ),
        next_step=f"pass an earlier analysis of this model, or drop `{flag}`.",
    )
