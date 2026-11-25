"""`packs` command."""

from __future__ import annotations

import typer
from otm_industry_packs.loader import list_pack_ids

from otm_cli.commands.bootstrap import console
from otm_cli.shared.render import safe


def register(app: typer.Typer) -> None:
    @app.command("packs")
    def cmd_packs() -> None:
        """List embedded industry packs."""
        console.print("[bold]Industry packs[/bold] (use: [cyan]otm analyze --pack ID[/cyan]):")
        for pid in list_pack_ids():
            # Pack ids are bundled, not user input, but the rule is uniform so an audit can
            # simply grep for an unescaped interpolation into `console.print`.
            console.print(f"  • {safe(pid)}")
