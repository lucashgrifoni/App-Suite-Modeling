"""Importing the PDF adapter leaves the optional renderer and signing stack unloaded.

Older xhtml2pdf releases loaded the certificate stack with the renderer. Newer releases make
signing optional. The adapter must defer the renderer either way. Probe in a fresh interpreter so
modules loaded by other tests cannot taint the result.
"""

from __future__ import annotations

import ast
import subprocess
import sys

_PROBE = (
    "import warnings, sys; warnings.simplefilter('ignore');"
    "import {module};"
    "print(sorted(m for m in sys.modules if m.split('.')[0] in "
    "{{'xhtml2pdf', 'oscrypto', 'pyhanko', 'pyhanko_certvalidator'}}))"
)


def _renderer_modules_after_importing(module: str) -> list[str]:
    completed = subprocess.run(
        [sys.executable, "-c", _PROBE.format(module=module)],
        capture_output=True,
        text=True,
        check=True,
    )
    parsed: list[str] = ast.literal_eval(completed.stdout.strip())
    return parsed


def test_importing_the_pdf_exporter_does_not_load_the_renderer_or_signing_stack() -> None:
    assert _renderer_modules_after_importing("otm_report_premium.pdf_export") == []


def test_the_probe_detects_an_explicit_renderer_import() -> None:
    assert "xhtml2pdf.pisa" in _renderer_modules_after_importing("xhtml2pdf.pisa")
