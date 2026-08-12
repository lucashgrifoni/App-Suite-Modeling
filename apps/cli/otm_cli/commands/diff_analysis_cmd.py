"""`diff-analysis` command."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from otm_threat_engine.gate import GatePolicy, evaluate_gate
from rich.panel import Panel

from otm_cli.application.diff_analysis_service import run_diff_analysis
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.emit import write_json_file
from otm_cli.shared.enums import DiffFormat
from otm_cli.shared.errors import CliUserError
from otm_cli.shared.gate import GATE_TRIP_EXIT_CODE, parse_fail_on, render_gate_result
from otm_cli.shared.render import safe


def register(app: typer.Typer) -> None:
    @app.command("diff-analysis")
    def cmd_diff_analysis(
        baseline: Annotated[Path, typer.Argument(help="AnalysisResult JSON (baseline).")],
        revised: Annotated[Path, typer.Argument(help="AnalysisResult JSON (revised).")],
        json_out: Path | None = typer.Option(None, "--json-out", help="Write AnalysisDiff to JSON."),
        fmt: DiffFormat = typer.Option(DiffFormat.text, "--format", "-f", help="text or json."),
        fail_on: str = typer.Option(
            "none",
            "--fail-on",
            # `\[` escaped so Rich does not swallow the allowed-value list as a style tag.
            help=("CI gate: exit 3 if a NEW or WORSENED threat reaches this band \\[none|low|medium|high|critical]."),
        ),
        fail_on_risk_increase: bool = typer.Option(
            False,
            "--fail-on-risk-increase",
            help="CI gate: exit 3 if any threat's risk score rises, even without changing band.",
        ),
    ) -> None:
        """Compare two analyze.json files without re-running the engine.

        Exit codes: 0 no gate trip · 1 usage error · 3 gate tripped.
        """
        try:
            policy = GatePolicy(fail_on=parse_fail_on(fail_on), fail_on_risk_increase=fail_on_risk_increase)
        except CliUserError as e:
            exit_on_cli_error(console, e)

        try:
            payload, lines, analysis_diff = run_diff_analysis(
                baseline,
                revised,
                fmt=fmt,
                require_same_engine_version=policy.active,
            )
        except CliUserError as e:
            exit_on_cli_error(console, e)

        if json_out:
            try:
                write_json_file(payload=payload, output=json_out)
            except CliUserError as e:
                exit_on_cli_error(console, e)
            console.print(f"[green]Analysis diff written to[/green] {safe(json_out.resolve())}")

        if fmt == DiffFormat.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            console.print(Panel(safe("\n".join(lines or [])), title="diff-analysis", border_style="magenta"))

        # Gate last: every artifact is on disk and stdout is complete before we can exit non-zero.
        if policy.active:
            result = evaluate_gate(analysis_diff, policy)
            print(render_gate_result(result), file=sys.stderr)
            if result.tripped:
                raise typer.Exit(GATE_TRIP_EXIT_CODE)
