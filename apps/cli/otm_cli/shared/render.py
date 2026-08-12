"""Markup-safe interpolation for the Rich console.

Rich reads `[...]` in a printed string as a style tag. Anything the CLI did not write literally
in its own source — a document title, a Pydantic field path, a component id, a file path, an
exception message — can contain brackets, and Rich then either deletes the text (`Checkout
[v2] rollout` printed as `Checkout  rollout`, `[components → 0 → id]` vanishing from a
validation error) or executes it, letting document content restyle the tool's own output.

Every such value goes through `safe()` before it is interpolated into a markup-enabled string.
Passing `markup=False` to `console.print` is not equivalent: it would also disable the CLI's own
`[red]`/`[bold]` styling on the same line.
"""

from __future__ import annotations

from rich.markup import escape


def safe(value: object) -> str:
    """Escape a user- or document-derived value so Rich renders it verbatim."""
    return escape("" if value is None else str(value))
