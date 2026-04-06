"""Shared CLI utilities (no Typer)."""

from otm_cli.shared.errors import CliUserError
from otm_cli.shared.version_util import installed_version

__all__ = ["CliUserError", "installed_version"]
