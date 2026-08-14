"""`report` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from otm_exporters.export_locale import recognized_export_locale
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
from otm_cli.shared.emit import input_paths, write_bytes_file, write_text_file
from otm_cli.shared.errors import CliUserError
from otm_cli.shared.render import safe


def _require_supported_locale(locale: str | None) -> None:
    """Reject a locale this report cannot render, instead of silently rendering another one.

    `--locale` is documented as a two-value option (`pt-BR` default, or `en`) but was typed as a
    free string and normalised with a server-style fallback, so `--locale ptBR` — the obvious
    typo, made by exactly the audience the pt-BR default is for — produced an English deliverable
    with exit 0 and no warning. That is a *different* language from the one the same command gives
    with no flag at all. Every sibling option (`--level`, `--format`, `--group-by`,
    `--methodology`) already refuses an unknown value with exit 2; this one now does too.

    The accepted set is whatever the shared resolver recognises, not a second list kept in step by
    hand: `pt`, `pt-PT`, `PT-BR`, `en-US` and friends keep working.
    """
    if locale is None or recognized_export_locale(locale) is not None:
        return
    raise typer.BadParameter(
        f"'{locale}' is not one of 'pt-BR', 'en'.",
        param_hint="--locale",
    )


def _emit_text_report(text: str, *, output: Path | None, label: str, sources: tuple[Path, ...]) -> None:
    """Write the report and say where, or print it to stdout so the caller can pipe it."""
    if output:
        try:
            write_text_file(content=text, output=output, sources=sources)
        except CliUserError as e:
            exit_on_cli_error(console, e)
        console.print(f"[green]{label}[/green] → {safe(output.resolve())}")
    else:
        print(text, end="")


def _emit_pdf_report(
    pdf_bytes: bytes,
    *,
    output: Path,
    locale_notice: str | None,
    sources: tuple[Path, ...],
    named_by_user: bool,
) -> None:
    """A PDF is never printed to stdout; without `--output` it lands on the report's default path.

    Esse default — `report-premium.pdf` no directório actual — é a **única** escrita do CLI para um
    caminho que o utilizador não nomeou, e substituía um ficheiro já existente sem dizer nada:
    correr o comando duas vezes na mesma pasta deitava fora o primeiro entregável, com exit 0.

    Substituir continua a ser o comportamento — recusar quebraria quem já corre isto em sequência,
    e reescrever para stdout não faz sentido para um PDF. O que muda é o silêncio: quando o
    destino não foi nomeado **e** já existia um ficheiro lá, isso é dito. Com `-o` explícito nada
    é avisado, porque aí o caminho é escolha de quem chamou, como em qualquer CLI.
    """
    replacing_unnamed = not named_by_user and output.exists()
    try:
        write_bytes_file(content=pdf_bytes, output=output, sources=sources)
    except CliUserError as e:
        exit_on_cli_error(console, e)
    if replacing_unnamed:
        console.print(
            f"[yellow]Note:[/yellow] replaced the existing {safe(output.name)} in this directory. "
            "Pass `-o <path>` to choose the destination."
        )
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
        _require_supported_locale(locale)

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

        inputs = input_paths(path, analysis_json, baseline_json)

        if isinstance(outcome, ReportLegacyResult):
            _emit_text_report(outcome.text, output=output, label="Report", sources=inputs)
            return

        if isinstance(outcome, ReportPremiumMarkdownResult):
            _emit_text_report(outcome.text, output=output, label="Report premium (Markdown)", sources=inputs)
            return

        if isinstance(outcome, ReportPremiumPdfResult):
            _emit_pdf_report(
                outcome.pdf_bytes,
                output=output or outcome.default_path,
                locale_notice=outcome.locale_notice,
                sources=inputs,
                named_by_user=output is not None,
            )
