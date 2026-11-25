"""Render `CliUserError` as Typer output."""

from __future__ import annotations

from typing import NoReturn

import typer
from rich.console import Console

from otm_cli.shared.errors import CliUserError
from otm_cli.shared.render import safe


def print_cli_error(console: Console, exc: CliUserError, *, header: str | None = None) -> None:
    """Print the whole error body without exiting.

    `header` replaces the default `Failure:` line — batch `validate` prefixes each error with the
    offending path instead. The body must stay identical in both callers: the batch branch used to
    print only the header, so a pre-commit run (which always passes several files) reported a
    blocked commit with no field, no cause and no next step.
    """
    first = header if header is not None else f"[red]Failure:[/red] {safe(exc.failed)}"
    console.print(
        f"{first}\n[yellow]Likely cause:[/yellow] {safe(exc.cause)}\n[cyan]Next step:[/cyan] {safe(exc.next_step)}"
    )
    if exc.validation_detail:
        console.print(f"[red]\n{safe(exc.validation_detail)}[/red]")


def exit_on_cli_error(console: Console, exc: CliUserError) -> NoReturn:
    """Print the error and end the command.

    Typed `NoReturn` because it always raises. Callers previously had to add an
    unreachable `raise` after it purely to convince the type checker that a value
    assigned in the `try` was bound afterwards — dead code that could never be
    covered by a test.
    """
    print_cli_error(console, exc)
    raise typer.Exit(exc.exit_code) from exc
