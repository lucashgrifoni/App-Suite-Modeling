"""Entry point for the `otm` command (console_scripts)."""

from __future__ import annotations

import os
import sys

# Ensure UTF-8 so that em-dash, bullets, arrows, accents and emojis render on
# legacy Windows consoles (CP850/CP1252) without mojibake or \uXXXX escapes.
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _stream in (sys.stdout, sys.stderr):
    reconfigure = getattr(_stream, "reconfigure", None)
    if callable(reconfigure):
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass

from otm_cli.cli import app as cli_app  # noqa: E402


def main() -> None:
    cli_app()


if __name__ == "__main__":
    main()
