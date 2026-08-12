"""`analyze` command."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from otm_core_schema.enums import ThreatModelMethodology
from otm_exporters import export_analysis_sarif
from otm_framework_mappings import framework_display_name
from otm_threat_engine.result import AnalysisResult
from rich.panel import Panel

from otm_cli.application.analyze_service import run_analyze
from otm_cli.commands.bootstrap import console
from otm_cli.commands.handle_errors import exit_on_cli_error
from otm_cli.shared.emit import write_json_file, write_text_file
from otm_cli.shared.enums import MethodologyOption
from otm_cli.shared.errors import CliUserError
from otm_cli.shared.render import safe


def _emit_json_output(result: AnalysisResult, json_out: Path, *, quiet: bool, model: Path) -> None:
    payload = result.model_dump(mode="json")
    try:
        write_json_file(payload=payload, output=json_out, sources=(model,))
    except CliUserError as e:
        exit_on_cli_error(console, e)
    if not quiet:
        console.print(f"[green]Analysis written to[/green] {safe(json_out.resolve())}")


def _emit_sarif_output(result: AnalysisResult, sarif_out: Path, *, quiet: bool, model: Path) -> None:
    try:
        write_text_file(content=export_analysis_sarif(result), output=sarif_out, sources=(model,))
    except CliUserError as e:
        exit_on_cli_error(console, e)
    if not quiet:
        console.print(f"[green]SARIF written to[/green] {safe(sarif_out.resolve())}")


def _emit_analysis_panel(result: AnalysisResult) -> None:
    s = result.summary
    pack_line = ""
    if result.industry_pack_id:
        pack_line = f"Pack: {safe(result.industry_pack_id)} · pack threats: {s.pack_threats_generated}\n"
    fw_line = ""
    if s.framework_ref_counts_by_catalog:
        bits = [f"{framework_display_name(k)}: {v}" for k, v in sorted(s.framework_ref_counts_by_catalog.items())]
        fw_line = "Framework refs: " + " · ".join(bits) + "\n"
    console.print(
        Panel.fit(
            f"[bold]{safe(result.document_title)}[/bold]\n\n"
            f"{pack_line}"
            f"{fw_line}"
            f"Structural warnings: {s.structural_findings}\n"
            f"Methodology: {result.methodology.value}\n"
            f"Cross-boundary flows: {s.trust_boundary_findings}\n"
            f"Base heuristics: {s.heuristic_threats_generated} new · "
            f"{s.heuristic_threats_skipped_duplicate} already covered\n"
            f"Highest score (L×I): {s.max_risk_score!s}\n"
            f"Engine: {result.engine_version}",
            title="analyze",
            border_style="cyan",
        )
    )
    if result.methodology_recommendation_reason:
        console.print(f"[dim]Auto recommendation:[/dim] {safe(result.methodology_recommendation_reason)}")
    if result.methodology == ThreatModelMethodology.PLOT4AI and result.ai_system_context:
        ctx = result.ai_system_context
        tags = ", ".join(ctx.pattern_tags[:6]) if ctx.pattern_tags else "—"
        # The surrounding brackets are literal output, not markup: escape the whole construct,
        # or Rich reads `[rag, agent]` as a style tag and prints `patterns ~ ` with nothing.
        console.print(f"[dim]PLOT4ai (AI):[/dim] patterns ~ {safe(f'[{tags}]')}")
        if ctx.primary_risk_surfaces:
            console.print(f"[dim]  Surface:[/dim] {safe(ctx.primary_risk_surfaces[0][:160])}")


def _emit_explainability(result: AnalysisResult, *, explain: bool) -> None:
    if not (explain and result.explanations):
        return
    console.print("\n[bold]Explainability[/bold] (first 15 entries)")
    for ex in result.explanations[:15]:
        cat = getattr(ex.category, "value", ex.category)
        console.print(f"  [cyan]{safe(cat)}[/cyan] · {safe(ex.subject)} — {safe(ex.message)}")


def _emit_audit_trail(result: AnalysisResult) -> None:
    if not (result.wizard_context_notes or result.wizard_signal_trace):
        return
    console.print("\n[bold]Assistant / audit trail[/bold] (summary)")
    for n in result.wizard_context_notes[:6]:
        console.print(f"  [dim]note:[/dim] {safe(n[:200])}")
    for tr in result.wizard_signal_trace[:8]:
        console.print(
            f"  [dim]{safe(tr.effect)}[/dim] `{safe(tr.source_tag[:64])}` ({tr.weight}) → {safe(tr.explanation[:160])}"
        )


def register(app: typer.Typer) -> None:
    @app.command("analyze")
    def cmd_analyze(
        path: Annotated[Path, typer.Argument(help=".otm.yaml file.")],
        quiet: bool = typer.Option(False, "--quiet", "-q", help="Exit code only; no summary."),
        json_out: Path | None = typer.Option(
            None,
            "--json-out",
            help="Write full analysis result to JSON.",
        ),
        sarif_out: Path | None = typer.Option(
            None,
            "--sarif-out",
            help="Write suggested threats as SARIF 2.1.0 (e.g. for GitHub code scanning).",
        ),
        pack: str | None = typer.Option(
            None,
            "--pack",
            "-p",
            help="Industry pack (see [cyan]otm packs[/cyan]).",
        ),
        rules: Path | None = typer.Option(
            None,
            "--rules",
            help="Organisation rule file (YAML) with custom heuristics. Additive; does not replace the engine.",
        ),
        methodology: MethodologyOption | None = typer.Option(
            None,
            "--methodology",
            "-m",
            help=("Methodology/engine (stride, linddun, nist_data_centric, octave_allegro, cia_die, pasta, plot4ai)."),
        ),
        auto_methodology: bool = typer.Option(
            False,
            "--auto-methodology",
            help="If no explicit methodology, apply automatic recommendation.",
        ),
        explain: bool = typer.Option(
            False,
            "--explain",
            "-x",
            help="Print a structured explainability summary to the terminal.",
        ),
    ) -> None:
        """Run the engine (STRIDE heuristics, boundaries, L×I risk, optional pack)."""
        if methodology is not None and auto_methodology:
            raise typer.BadParameter(
                "`--methodology/-m` and `--auto-methodology` are mutually exclusive; pass only one.",
                param_hint="--methodology / --auto-methodology",
            )
        try:
            result = run_analyze(
                path,
                pack=pack,
                methodology=methodology,
                auto_methodology=auto_methodology,
                rules=rules,
            )
        except CliUserError as e:
            exit_on_cli_error(console, e)

        if json_out:
            _emit_json_output(result, json_out, quiet=quiet, model=path)
        if sarif_out:
            _emit_sarif_output(result, sarif_out, quiet=quiet, model=path)
        if quiet:
            raise typer.Exit(0)

        _emit_analysis_panel(result)
        _emit_explainability(result, explain=explain)
        _emit_audit_trail(result)
