"""CLI user-facing errors — testable without Typer (`raise CliUserError`)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CliUserError(Exception):
    """
    Expected CLI failure (validation, I/O, missing pack).

    The command layer turns this into Rich output + `typer.Exit(exit_code)`.
    """

    exit_code: int = 1
    failed: str = ""
    cause: str = ""
    next_step: str = ""
    validation_detail: str | None = None
    message: str = field(default="", repr=False)

    def __post_init__(self) -> None:
        if not self.message:
            parts = [
                f"Failure: {self.failed}",
                f"Cause: {self.cause}",
                f"Next step: {self.next_step}",
            ]
            self.message = "\n".join(parts)
