"""`packs` command."""

from __future__ import annotations

import typer
from otm_industry_packs.loader import list_pack_ids

from otm_cli.commands.bootstrap import listing_console
from otm_cli.shared.render import safe


def register(app: typer.Typer) -> None:
    @app.command("packs")
    def cmd_packs() -> None:
        """List embedded industry packs."""
        pack_ids = list_pack_ids()
        listing_console.print("[bold]Industry packs[/bold] (use: [cyan]otm analyze --pack ID[/cyan]):")
        for pid in pack_ids:
            listing_console.print(f"  • {safe(pid)}")
