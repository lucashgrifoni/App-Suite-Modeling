"""`precheck` command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel

from otm_cli.application.precheck_service import run_precheck
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.emit import write_json_file
from otm_cli.shared.enums import MethodologyOption
from otm_cli.shared.errors import CliUserError


def register(app: typer.Typer) -> None:
    @app.command("precheck")
    def cmd_precheck(
        path: Annotated[Path, typer.Argument(help=".otm.yaml / .yml file.")],
        json_out: Path | None = typer.Option(
            None,
            "--json-out",
            help="Write pre-check + methodology completeness to JSON.",
        ),
        methodology: MethodologyOption | None = typer.Option(
            None,
            "--methodology",
            "-m",
            help="Methodology for completeness scoring (default: document.model.methodology).",
        ),
    ) -> None:
        """Model completeness pre-check (score, band, matrix) without running STRIDE."""
        try:
            payload = run_precheck(path, methodology=methodology)
        except CliUserError as e:
            exit_on_cli_error(console, e)
        if json_out:
            write_json_file(payload=payload, output=json_out)
            console.print(f"[green]Pre-check written to[/green] {json_out.resolve()}")
        else:
            console.print(
                Panel.fit(
                    json.dumps(payload, indent=2, ensure_ascii=False),
                    title="precheck",
                    border_style="cyan",
                )
            )
