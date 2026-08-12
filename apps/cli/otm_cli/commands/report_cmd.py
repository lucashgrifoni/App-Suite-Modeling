"""`report` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from otm_report_premium.enums import ReportFormat as PremiumReportFormat
from otm_report_premium.enums import ReportLevel as PremiumReportLevel

from otm_cli.application.report_service import (
    ReportLegacyResult,
    ReportPremiumMarkdownResult,
    ReportPremiumPdfResult,
    run_report,
)
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.emit import write_bytes_file, write_text_file
from otm_cli.shared.errors import CliUserError
from otm_cli.shared.render import safe


def _emit_text_report(text: str, *, output: Path | None, label: str) -> None:
    """Write the report and say where, or print it to stdout so the caller can pipe it."""
    if output:
        try:
            write_text_file(content=text, output=output)
        except CliUserError as e:
            exit_on_cli_error(console, e)
        console.print(f"[green]{label}[/green] → {safe(output.resolve())}")
    else:
        print(text, end="")


def _emit_pdf_report(pdf_bytes: bytes, *, output: Path, locale_notice: str | None) -> None:
    """A PDF is never printed to stdout; without `--output` it lands on the report's default path."""
    try:
        write_bytes_file(content=pdf_bytes, output=output)
    except CliUserError as e:
        exit_on_cli_error(console, e)
    if locale_notice:
        console.print(f"[yellow]Note:[/yellow] {safe(locale_notice)}")
    console.print(f"[green]Report premium (PDF)[/green] → {safe(output.resolve())}")


def register(app: typer.Typer) -> None:
    @app.command("report")
    def cmd_report(
        path: Annotated[Path, typer.Argument(help=".otm.yaml file.")],
        output: Annotated[
            Path | None,
            typer.Option("--output", "-o", help="Write report (default: stdout for text)."),
        ] = None,
        pack: str | None = typer.Option(
            None,
            "--pack",
            "-p",
            help="Industry pack for analysis.",
        ),
        level: Annotated[
            PremiumReportLevel | None,
            typer.Option(
                "--level",
                "-l",
                help=(
                    "Premium report: executive | standard | deep. "
                    "If omitted, generates legacy report (model + analysis in Markdown)."
                ),
            ),
        ] = None,
        report_format: Annotated[
            PremiumReportFormat,
            typer.Option(
                "--format",
                "-f",
                help="With --level: markdown (default) or pdf.",
            ),
        ] = PremiumReportFormat.MARKDOWN,
        analysis_json: Annotated[
            Path | None,
            typer.Option(
                "--analysis-json",
                help="Reuse `AnalysisResult` JSON instead of running the engine.",
            ),
        ] = None,
        baseline_json: Annotated[
            Path | None,
            typer.Option(
                "--baseline",
                help="Prior analysis JSON for baseline/diff section in premium report.",
            ),
        ] = None,
        locale: Annotated[
            str | None,
            typer.Option(
                "--locale",
                help="Premium report structural text locale: pt-BR (default) or en.",
            ),
        ] = None,
    ) -> None:
        """Legacy report (Markdown) or premium report (executive/standard/deep)."""
        try:
            outcome = run_report(
                path,
                pack=pack,
                level=level,
                report_format=report_format,
                analysis_json=analysis_json,
                baseline_json=baseline_json,
                locale=locale,
            )
        except CliUserError as e:
            exit_on_cli_error(console, e)

        if isinstance(outcome, ReportLegacyResult):
            _emit_text_report(outcome.text, output=output, label="Report")
            return

        if isinstance(outcome, ReportPremiumMarkdownResult):
            _emit_text_report(outcome.text, output=output, label="Report premium (Markdown)")
            return

        if isinstance(outcome, ReportPremiumPdfResult):
            _emit_pdf_report(
                outcome.pdf_bytes,
                output=output or outcome.default_path,
                locale_notice=outcome.locale_notice,
            )
