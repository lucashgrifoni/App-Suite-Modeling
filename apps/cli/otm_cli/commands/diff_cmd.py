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
from otm_cli.shared.enums import DiffFormat, MethodologyOption
from otm_cli.shared.errors import CliUserError
from otm_cli.shared.gate import GATE_TRIP_EXIT_CODE, parse_fail_on, render_gate_result
from otm_cli.shared.render import safe


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


def _write_diff_json(payload: dict, output: Path, sources: tuple[Path, ...]) -> None:
    """Write the `--json-out` artifact, or render the CLI error and exit with its code."""
    try:
        write_json_file(payload=payload, output=output, sources=sources)
    except CliUserError as e:
        exit_on_cli_error(console, e)
    console.print(f"[green]Diff written to[/green] {safe(output.resolve())}")


def _emit_diff(
    fmt: DiffFormat,
    *,
    json_print: str | None,
    md_text: str | None,
    panel_text: str | None,
    summary_only: bool,
) -> None:
    """`json` and `markdown` go to stdout verbatim so they stay pipeable; text gets a panel."""
    if fmt == DiffFormat.json:
        body = json_print or ""
        print(body, end="" if body.endswith("\n") else "\n")
        return
    if fmt == DiffFormat.markdown:
        print(md_text or "", end="")
        return
    # The panel body carries document titles AND its own `[metadata]`/`[components]`
    # section headers; unescaped, Rich reads both as style tags and deletes them.
    console.print(
        Panel(
            safe(panel_text or ""),
            title="diff (summary)" if summary_only else "diff",
            border_style="blue",
        )
    )


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
        rules: Path | None = typer.Option(
            None,
            "--rules",
            help=(
                "Organisation rule file (YAML) applied to BOTH sides when --with-analysis is set, "
                "so an org-rule violation introduced by the change trips the gate."
            ),
        ),
        methodology: MethodologyOption | None = typer.Option(
            None,
            "--methodology",
            "-m",
            help=(
                "Methodology/engine used for BOTH sides of the comparison "
                "(stride, linddun, nist_data_centric, octave_allegro, cia_die, pasta, plot4ai). "
                "Must match the lens `otm analyze` runs, or the gate judges a different threat set."
            ),
        ),
        auto_methodology: bool = typer.Option(
            False,
            "--auto-methodology",
            help="If no explicit methodology, apply automatic recommendation to both sides.",
        ),
        summary_only: bool = typer.Option(
            False,
            "--summary-only",
            help="Show only summary and key insights (text/markdown).",
        ),
        fail_on: str = typer.Option(
            "none",
            "--fail-on",
            # The `\[` escape is required: Rich renders Typer help and would otherwise parse
            # `[none|low|...]` as a style tag and silently drop the list of allowed values.
            help=(
                "CI gate: exit 3 if a NEW or WORSENED threat reaches this band "
                "\\[none|low|medium|high|critical]. Implies --with-analysis."
            ),
        ),
        fail_on_risk_increase: bool = typer.Option(
            False,
            "--fail-on-risk-increase",
            help=(
                "CI gate: exit 3 if any threat's risk score rises, even without changing band. Implies --with-analysis."
            ),
        ),
    ) -> None:
        """Compare two threat model versions.

        Exit codes: 0 no gate trip · 1 usage error · 3 gate tripped.
        """
        if methodology is not None and auto_methodology:
            raise typer.BadParameter(
                "`--methodology/-m` and `--auto-methodology` are mutually exclusive; pass only one.",
                param_hint="--methodology / --auto-methodology",
            )

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
                methodology=methodology,
                auto_methodology=auto_methodology,
                rules=rules,
            )
        except CliUserError as e:
            exit_on_cli_error(console, e)

        if json_out:
            _write_diff_json(out_payload, json_out, (baseline, revised))

        _emit_diff(
            fmt,
            json_print=json_print,
            md_text=md_text,
            panel_text=panel_text,
            summary_only=summary_only,
        )

        _apply_gate(analysis_diff, policy)
