"""The `[report]` extra drags a certificate-validation stack in. Keep it where it is.

`report = ["xhtml2pdf>=0.2.15"]` is the whole extra, and xhtml2pdf's metadata requires pyHanko and
pyhanko-certvalidator unconditionally -- its PDF *signing* capability -- even though this project
only renders HTML to PDF and signs nothing. pyhanko-certvalidator requires `oscrypto>=1.1.0`, and
the newest oscrypto pip can resolve is 1.3.0: a library for TLS sockets, key generation,
encryption, signing and verification against the OS crypto libraries, with no newer release to
move to. Measured, importing `xhtml2pdf.pisa` really does load it (`oscrypto.__version__` 1.3.0,
`oscrypto._asn1` and friends in `sys.modules`).

Nothing here is exploitable today: no advisory applies to 1.3.0, no attacker-controlled bytes were
traced into its routines, and the whole path is behind an optional extra. The recorded risk is
remediation latency -- if an advisory does land there is no upstream fix to adopt, and the choice
would be between shipping a known-vulnerable dependency and withdrawing an advertised feature.
That decision wants an owner and an expiry before an incident, not during one.

What this file protects is the one property that bounds the exposure and that a refactor could
quietly lose: the import is *lazy*. `otm_report_premium.pdf_export` can be imported -- and is, by
`otm report`, by the API router, and by module discovery -- without loading a single line of
oscrypto or pyHanko. Move that `xhtml2pdf` import to module scope and every command in the product
starts paying for the crypto stack; the test below fails if that happens.

It runs in a subprocess on purpose: by the time this test executes, another test in the session has
almost certainly imported xhtml2pdf already, and `sys.modules` in this process would say nothing
about what importing `pdf_export` costs on its own.
"""

from __future__ import annotations

import ast
import subprocess
import sys

_PROBE = (
    "import warnings, sys; warnings.simplefilter('ignore');"
    "import {module};"
    "print(sorted(m for m in sys.modules if m.split('.')[0] in {{'oscrypto', 'pyhanko', 'pyhanko_certvalidator'}}))"
)


def _crypto_modules_after_importing(module: str) -> list[str]:
    completed = subprocess.run(
        [sys.executable, "-c", _PROBE.format(module=module)],
        capture_output=True,
        text=True,
        check=True,
    )
    parsed: list[str] = ast.literal_eval(completed.stdout.strip())
    return parsed


def test_importing_the_pdf_exporter_does_not_load_the_certificate_stack() -> None:
    """The lazy import is what keeps the unmaintained crypto chain off every other command."""
    assert _crypto_modules_after_importing("otm_report_premium.pdf_export") == []


def test_the_certificate_stack_really_is_behind_xhtml2pdf() -> None:
    """Control: the test above would pass just as well if the chain had quietly disappeared."""
    assert _crypto_modules_after_importing("xhtml2pdf.pisa") != []
