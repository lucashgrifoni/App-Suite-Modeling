"""Markup-safe interpolation for the Rich console.

Rich reads `[...]` in a printed string as a style tag. Anything the CLI did not write literally
in its own source — a document title, a Pydantic field path, a component id, a file path, an
exception message — can contain brackets, and Rich then either deletes the text (`Checkout
[v2] rollout` printed as `Checkout  rollout`, `[components → 0 → id]` vanishing from a
validation error) or executes it, letting document content restyle the tool's own output.

Every such value goes through `safe()` before it is interpolated into a markup-enabled string.
Passing `markup=False` to `console.print` is not equivalent: it would also disable the CLI's own
`[red]`/`[bold]` styling on the same line.

Brackets are only half the problem. The same values can also carry terminal control sequences,
and Rich does not remove those: its `strip_control_codes` list is BEL, BS, VT, FF and CR, which
deliberately excludes ESC (0x1B). A `metadata.title` of `\x1b[2K\x1b[G\x1b[31mFAKE ERROR` therefore
reached the terminal intact and repainted the line the CLI had just written — and because
`.pre-commit-hooks.yaml` ships `entry: otm validate` and pre-commit hands the hook every matching
path at once, a title in the second file carrying `\x1b[1A\x1b[2K` pairs walked the cursor back
over the first file's `Invalid` block and forged `All 2 files valid.` while the process still
exited 1. Document content chose what the reviewer read. So `safe()` neutralises both: control
characters are removed, then the markup escape runs.
"""

from __future__ import annotations

import re

from rich.markup import escape

#: Characters a terminal acts on instead of printing: C0 minus TAB/LF, DEL, and the C1 block.
#: This is the set `otm_exporters.markdown_text._CONTROL_CHARS` already removes on the Markdown
#: surface, extended with ESC (0x1B) — the byte that carries CSI and OSC — and with C1, because a
#: terminal honouring 8-bit controls reads U+009B as CSI, which would walk around an ESC-only
#: filter. Removed rather than replaced: they represent nothing an author wanted shown.
#:
#: TAB and LF are excluded on purpose, and that exclusion is load-bearing. `safe()` is applied to
#: values that are *legitimately* multi-line — `precheck` panels a `json.dumps(..., indent=2)`,
#: `diff-analysis` panels a `"\n".join(lines)`, `handle_errors` panels a multi-line
#: `validation_detail`, `templates --show` panels a whole YAML file. Flattening line breaks here
#: would neutralise the attack by destroying the feature; the escape is what has to go, not the
#: layout. CR is inside the range, matching what Rich already did with it.
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]")


def safe(value: object) -> str:
    """Neutralise a user- or document-derived value: no terminal control, no Rich markup.

    Both properties matter and neither is truncation — the surrounding text is preserved
    character for character, so the diagnostic the value belongs to stays readable.
    """
    return escape(_CONTROL_CHARS.sub("", "" if value is None else str(value)))
