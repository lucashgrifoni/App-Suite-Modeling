"""`recommend-methodology` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel

from otm_cli.application.recommend_service import run_recommend_methodology
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.errors import CliUserError
from otm_cli.shared.render import safe


def register(app: typer.Typer) -> None:
    @app.command("recommend-methodology")
    def cmd_recommend_methodology(
        path: Annotated[Path, typer.Argument(help=".otm.yaml file.")],
    ) -> None:
        """Suggest primary methodology from model context."""
        try:
            rec = run_recommend_methodology(path)
        except CliUserError as e:
            exit_on_cli_error(console, e)
        console.print(
            Panel.fit(
                f"Suggested methodology: [bold]{safe(rec.methodology.value)}[/bold]\n\nReason: {safe(rec.reason)}",
                title="recommend-methodology",
                border_style="magenta",
            )
        )
