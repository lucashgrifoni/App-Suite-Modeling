"""`diff-analysis` command."""

from __future__ import annotations

import json
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
from otm_cli.shared.gate import parse_fail_on, report_gate_verdict
from otm_cli.shared.render import safe


def register(app: typer.Typer) -> None:
    @app.command("diff-analysis")
    def cmd_diff_analysis(
        baseline: Annotated[Path, typer.Argument(help="AnalysisResult JSON (baseline).")],
        revised: Annotated[Path, typer.Argument(help="AnalysisResult JSON (revised).")],
        json_out: Path | None = typer.Option(None, "--json-out", help="Write AnalysisDiff to JSON."),
        fmt: DiffFormat = typer.Option(DiffFormat.text, "--format", "-f", help="text | json | markdown"),
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

        Exit codes: 0 no gate trip · 1 usage error, including an out-of-range `--fail-on` value,
        or an armed gate with no verdict (the two analyses are not comparable) · 2 parsing error
        raised by Typer/Click: unknown flag, missing argument, invalid enum value on `--format`
        · 3 gate tripped.
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
                write_json_file(payload=payload, output=json_out, sources=(baseline, revised))
            except CliUserError as e:
                exit_on_cli_error(console, e)
            console.print(f"[green]Analysis diff written to[/green] {safe(json_out.resolve())}")

        if fmt == DiffFormat.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        elif fmt == DiffFormat.markdown:
            # Cru, como em `diff_cmd`: quem pede markdown vai canalizá-lo para um ficheiro, e um
            # painel do Rich no meio faria dele lixo. Antes disto `markdown` caía no `else`.
            print("\n".join(lines or []))
        else:
            console.print(Panel(safe("\n".join(lines or [])), title="diff-analysis", border_style="magenta"))

        # Gate last: every artifact is on disk and stdout is complete before we can exit non-zero.
        if policy.active:
            # Same mapping and same ordering as `otm diff`, including the non-zero exit for a gate
            # that could not judge: the two commands arm the same policy and must answer CI the
            # same way, whether or not anyone is still reading the report.
            code = report_gate_verdict(evaluate_gate(analysis_diff, policy))
            if code:
                raise typer.Exit(code)
