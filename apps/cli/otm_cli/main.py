"""Entry point for the `otm` command (console_scripts)."""

from __future__ import annotations

from otm_cli.cli import app as cli_app


def main() -> None:
    cli_app()


if __name__ == "__main__":
    main()
