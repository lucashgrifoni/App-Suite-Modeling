"""Shared Rich console for the CLI."""

from __future__ import annotations

from rich.console import Console

console = Console(stderr=True)
