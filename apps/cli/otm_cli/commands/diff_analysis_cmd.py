"""`diff-analysis` command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.panel import Panel

from otm_cli.application.diff_analysis_service import run_diff_analysis
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.emit import write_json_file
from otm_cli.shared.enums import DiffFormat
from otm_cli.shared.errors import CliUserError


def register(app: typer.Typer) -> None:
    @app.command("diff-analysis")
    def cmd_diff_analysis(
        baseline: Annotated[Path, typer.Argument(help="AnalysisResult JSON (baseline).")],
        revised: Annotated[Path, typer.Argument(help="AnalysisResult JSON (revised).")],
        json_out: Path | None = typer.Option(None, "--json-out", help="Write AnalysisDiff to JSON."),
        fmt: DiffFormat = typer.Option(DiffFormat.text, "--format", "-f", help="text or json."),
    ) -> None:
        """Compare two analyze.json files without re-running the engine."""
        try:
            payload, lines = run_diff_analysis(baseline, revised, fmt=fmt)
        except CliUserError as e:
            exit_on_cli_error(console, e)

        if json_out:
            try:
                write_json_file(payload=payload, output=json_out)
            except CliUserError as e:
                exit_on_cli_error(console, e)
            console.print(f"[green]Analysis diff written to[/green] {json_out.resolve()}")
        if fmt == DiffFormat.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return
        console.print(Panel("\n".join(lines or []), title="diff-analysis", border_style="magenta"))
