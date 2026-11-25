"""Shared Rich console for the CLI."""

from __future__ import annotations

from rich.console import Console


class _ListingConsole(Console):
    def on_broken_pipe(self) -> None:
        """A reader can stop paging a catalog without causing a command failure."""
        raise SystemExit(0)


# `legacy_windows=False` disables Rich's downgrade to the old cmd.exe code
# page; combined with the UTF-8 stream reconfigure in `otm_cli.main`, this
# keeps em-dashes, bullets, arrows and accents intact on Windows Terminal,
# PowerShell 7 and pwsh-in-VS-Code without requiring `chcp 65001`.
console = Console(stderr=True, legacy_windows=False)
listing_console = _ListingConsole(stderr=True, legacy_windows=False)
