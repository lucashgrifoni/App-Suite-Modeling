"""Use case: list explanations from JSON."""

from __future__ import annotations

import json
from pathlib import Path

from otm_cli.shared.errors import CliUserError


def run_explain(
    path: Path,
    *,
    kind: str,
    category: str | None,
    limit: int,
) -> list[tuple[str, str, str]]:
    """
    Return a list of (category, subject, message).

    Raises CliUserError(exit_code=2) for invalid kind.
    Empty list means nothing to show (command may exit 0 with a warning).
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:
        raise CliUserError(
            exit_code=1,
            failed=f"reading `{path}`.",
            cause=str(e),
            next_step="confirm the file path.",
        ) from e
    except json.JSONDecodeError as e:
        raise CliUserError(
            exit_code=1,
            failed="invalid JSON.",
            cause=str(e),
            next_step="confirm the file contains valid JSON.",
        ) from e
    explanations: list = []
    if kind == "analysis":
        explanations = list(raw.get("explanations") or [])
    elif kind == "compare":
        explanations = list(raw.get("explanations") or [])
    else:
        raise CliUserError(
            exit_code=2,
            failed="invalid --from option.",
            cause="use analysis or compare.",
            next_step="run `otm explain --help`.",
        )
    if not explanations:
        return []
    if category:
        explanations = [
            e
            for e in explanations
            if str(e.get("category", "")).strip().lower() == category.lower()
        ]
    out: list[tuple[str, str, str]] = []
    for item in explanations[:limit]:
        subj = str(item.get("subject", ""))
        msg = str(item.get("message", ""))
        cat = str(item.get("category", ""))
        out.append((cat, subj, msg))
    return out
