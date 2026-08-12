"""Use case: list explanations from JSON."""

from __future__ import annotations

import json
from pathlib import Path

from otm_cli.shared.errors import CliUserError

_KINDS = ("analysis", "compare")

#: Fields that identify a file as one kind and rule out the other. `AnalysisResult` carries
#: `engine_version`; `ThreatModelComparisonResult` carries `structural`. Neither is present in a
#: hand-written `{"explanations": [...]}` file, so those keep working under either `--from`.
_ANALYSIS_MARKER = "engine_version"
_COMPARE_MARKER = "structural"


def _reject_wrong_kind(raw: dict, kind: str) -> None:
    """`--from` advertises the input kind, so it has to actually check it.

    Only a positive identification of the *other* kind is rejected: guessing beyond that would
    turn a legitimate trimmed-down file into a hard failure.
    """
    looks_analysis = _ANALYSIS_MARKER in raw and _COMPARE_MARKER not in raw
    looks_compare = _COMPARE_MARKER in raw and _ANALYSIS_MARKER not in raw
    if kind == "analysis" and looks_compare:
        actual, expected, article = "compare", "analysis", "a"
    elif kind == "compare" and looks_analysis:
        actual, expected, article = "analysis", "compare", "an"
    else:
        return
    raise CliUserError(
        exit_code=1,
        failed=f"`--from {expected}` does not match the file.",
        cause=f"this looks like {article} {actual} JSON.",
        next_step=f"re-run with `--from {actual}`.",
    )


def run_explain(
    path: Path,
    *,
    kind: str,
    category: str | None,
    limit: int,
) -> list[tuple[str, str, str]]:
    """
    Return a list of (category, subject, message).

    Raises CliUserError(exit_code=2) for an invalid `--from` or a non-positive `--limit`.
    Empty list means nothing to show (command may exit 0 with a warning).
    """
    if kind not in _KINDS:
        raise CliUserError(
            exit_code=2,
            failed="invalid --from option.",
            cause="use analysis or compare.",
            next_step="run `otm explain --help`.",
        )
    if limit < 1:
        # `explanations[:0]` reported a populated file as empty and `explanations[:-3]` hid the
        # LAST three rows — the opposite of a maximum. Neither can be what the caller meant.
        raise CliUserError(
            exit_code=2,
            failed=f"invalid --limit value `{limit}`.",
            cause="--limit is a maximum number of lines and must be 1 or greater.",
            next_step="drop the flag to use the default, or pass a positive number.",
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    # UnicodeDecodeError belongs here rather than with the JSON errors: it comes out of
    # `read_text`, so the file was never decoded at all. It is a ValueError, not an OSError, and
    # used to escape both handlers and reach the user as a raw traceback on any analysis JSON a
    # Windows editor had saved as cp1252/latin-1.
    except (OSError, UnicodeDecodeError) as e:
        raise CliUserError(
            exit_code=1,
            failed=f"reading `{path}`.",
            cause=str(e),
            next_step="confirm the file path and that the file is UTF-8 encoded.",
        ) from e
    except json.JSONDecodeError as e:
        raise CliUserError(
            exit_code=1,
            failed="invalid JSON.",
            cause=str(e),
            next_step="confirm the file contains valid JSON.",
        ) from e
    if not isinstance(raw, dict):
        raise CliUserError(
            exit_code=1,
            failed="unexpected JSON shape.",
            cause=f"expected an object, got {type(raw).__name__}.",
            next_step="pass an `analysis.json` from `otm analyze --json-out`.",
        )
    _reject_wrong_kind(raw, kind)
    # Both kinds expose explanations under the same key — the difference `--from` encodes is
    # which document the file is, which `_reject_wrong_kind` above is what actually enforces.
    explanations = list(raw.get("explanations") or [])
    if not explanations:
        return []
    if category:
        explanations = [e for e in explanations if str(e.get("category", "")).strip().lower() == category.lower()]
    out: list[tuple[str, str, str]] = []
    for item in explanations[:limit]:
        subj = str(item.get("subject", ""))
        msg = str(item.get("message", ""))
        cat = str(item.get("category", ""))
        out.append((cat, subj, msg))
    return out
