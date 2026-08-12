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

from otm_cli.shared.errors import CliUserError


def load_custom_rules_or_raise(rules: Path | None) -> CustomRuleSet | None:
    """`None` in, `None` out; a malformed file becomes a `CliUserError`, never a raw traceback."""
    if rules is None:
        return None
    try:
        return load_custom_rules(rules)
    except ValueError as exc:
        # The engine raises plain ValueError; the CLI owns the exit code and the wording.
        raise CliUserError(
            exit_code=1,
            failed=f"loading custom rules from `{rules}`.",
            cause=str(exc),
            next_step="fix the rules file; see docs/features/CUSTOM_RULES.md for the format.",
        ) from exc
