"""`diff` command."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer
from otm_threat_engine.comparison_models import AnalysisDiff
from otm_threat_engine.gate import GatePolicy, evaluate_gate
from rich.panel import Panel

from otm_cli.application.diff_service import run_model_diff
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.emit import write_json_file
from otm_cli.shared.enums import DiffFormat
from otm_cli.shared.errors import CliUserError
from otm_cli.shared.gate import GATE_TRIP_EXIT_CODE, parse_fail_on, render_gate_result


def _apply_gate(analysis_diff: AnalysisDiff | None, policy: GatePolicy) -> None:
    """Evaluate the gate LAST, after every artifact and stdout payload has been emitted.

    CI wants the diff artifact most on the runs where the gate trips, so exiting early would
    destroy the evidence. The verdict goes to stderr so `--format json` stdout stays parseable.
    """
    if not policy.active or analysis_diff is None:
        return
    result = evaluate_gate(analysis_diff, policy)
    print(render_gate_result(result), file=sys.stderr)
    if result.tripped:
        raise typer.Exit(GATE_TRIP_EXIT_CODE)


def register(app: typer.Typer) -> None:
    @app.command("diff")
    def cmd_diff(
        baseline: Annotated[Path, typer.Argument(help="Previous version (baseline) .otm.yaml.")],
        revised: Annotated[Path, typer.Argument(help="New version (revised) .otm.yaml.")],
        json_out: Path | None = typer.Option(
            None,
            "--json-out",
            help="Write result to JSON.",
        ),
        fmt: DiffFormat = typer.Option(
            DiffFormat.text,
            "--format",
            "-f",
            help="text | json | markdown",
        ),
        with_analysis: bool = typer.Option(
            False,
            "--with-analysis",
            help="Run the engine on both YAML files and include risk/heuristic delta.",
        ),
        pack: str | None = typer.Option(
            None,
            "--pack",
            "-p",
            help="Industry pack when --with-analysis is set.",
        ),
        summary_only: bool = typer.Option(
            False,
            "--summary-only",
            help="Show only summary and key insights (text/markdown).",
        ),
        fail_on: str = typer.Option(
            "none",
            "--fail-on",
            help=(
                "CI gate: exit 3 if a NEW or WORSENED threat reaches this band "
                "[none|low|medium|high|critical]. Implies --with-analysis."
            ),
        ),
        fail_on_risk_increase: bool = typer.Option(
            False,
            "--fail-on-risk-increase",
            help="CI gate: exit 3 if the maximum risk score rises at all. Implies --with-analysis.",
        ),
    ) -> None:
        """Compare two threat model versions.

        Exit codes: 0 no gate trip · 1 usage error · 3 gate tripped.
        """
        try:
            policy = GatePolicy(fail_on=parse_fail_on(fail_on), fail_on_risk_increase=fail_on_risk_increase)
        except CliUserError as e:
            exit_on_cli_error(console, e)

        # An armed gate needs the engine delta. Without it the gate could never trip — a silent
        # pass, the worst failure mode for a security gate — so arming it turns the analysis on.
        run_analysis = with_analysis or policy.active

        try:
            out_payload, json_print, md_text, panel_text, analysis_diff = run_model_diff(
                baseline,
                revised,
                with_analysis=run_analysis,
                pack=pack,
                fmt=fmt,
                summary_only=summary_only,
            )
        except CliUserError as e:
            exit_on_cli_error(console, e)

        if json_out:
            try:
                write_json_file(payload=out_payload, output=json_out)
            except CliUserError as e:
                exit_on_cli_error(console, e)
            console.print(f"[green]Diff written to[/green] {json_out.resolve()}")

        if fmt == DiffFormat.json:
            body = json_print or ""
            print(body, end="" if body.endswith("\n") else "\n")
        elif fmt == DiffFormat.markdown:
            print(md_text or "", end="")
        elif summary_only:
            console.print(Panel(panel_text or "", title="diff (summary)", border_style="blue"))
        else:
            console.print(Panel(panel_text or "", title="diff", border_style="blue"))

        _apply_gate(analysis_diff, policy)
