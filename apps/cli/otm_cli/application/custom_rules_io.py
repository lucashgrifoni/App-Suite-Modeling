"""Load an organisation rule file with the CLI's error contract.

Shared by `otm analyze --rules` and `otm diff --rules` so both report a broken rule file the
same way. `otm diff` needs it because the drift gate is the command the composite action runs
(`action.yml`), and `docs/features/CUSTOM_RULES.md` promises that "rules flow into everything
downstream, including the drift gate" — which could not be true while `diff` had no way to load
them.
"""

from __future__ import annotations

from pathlib import Path

from otm_threat_engine.custom_rules import CustomRuleSet, load_custom_rules
from pydantic import ValidationError

from otm_cli.io_util import format_validation_error
from otm_cli.shared.errors import CliUserError

_NEXT_STEP = "fix the rules file; see docs/features/CUSTOM_RULES.md for the format."
_RULES_HEADER = "The rules file is not valid:"


def load_custom_rules_or_raise(rules: Path | None) -> CustomRuleSet | None:
    """`None` in, `None` out; a malformed file becomes a `CliUserError`, never a raw traceback."""
    if rules is None:
        return None
    try:
        return load_custom_rules(rules)
    # `ValidationError` is a `ValueError`, so it has to be caught first or the branch below eats
    # it. It used to: the whole Pydantic dump — `[type=value_error, input_value={...}]` and the
    # `errors.pydantic.dev` URL — went into the `Likely cause:` slot, in a feature whose docs
    # promise a loud, readable failure. The field list users act on survives inside `msg`; only
    # the framework packaging is dropped, and it is rendered like every other CLI validation
    # error.
    except ValidationError as exc:
        raise CliUserError(
            exit_code=1,
            failed=f"loading custom rules from `{rules}`.",
            cause="the file does not match the custom-rules schema.",
            next_step=_NEXT_STEP,
            validation_detail=format_validation_error(exc, header=_RULES_HEADER),
        ) from exc
    except ValueError as exc:
        # The loader's own errors (not found, too large, not YAML, not a mapping) are already
        # written for a human; the CLI owns the exit code and keeps the wording.
        raise CliUserError(
            exit_code=1,
            failed=f"loading custom rules from `{rules}`.",
            cause=str(exc),
            next_step=_NEXT_STEP,
        ) from exc
