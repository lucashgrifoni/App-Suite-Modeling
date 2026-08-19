"""P4 regression — one missing brace must not rewrite the threat model, nor stall the server.

`_iter_resource_blocks` walks forward from each `resource "t" "n" {` header until the braces
balance. When they never balance it walks to end-of-text, and it does that **once per header**,
materialising every body at `terraform_import.py`'s `list(...)`. Two defects fall out of the same
line, and the quiet one is the worse of the two.

*The quiet one.* A block's body has exactly one consumer: `_public_ingress_hint`, which searches it
for `0.0.0.0/0`. With the braces unbalanced the bodies are overlapping suffixes, so an open CIDR on
a late resource is inside the body of every resource declared before it. A single missing brace
therefore moves an `internal = true` load balancer into `tb_internet_facing` and invents exposure
threats against it — a wrong threat model, produced silently, from input the parser accepted.

*The loud one.* The same suffixes cost O(bytes x headers) to scan and to retain: measured, 54 KB of
unbalanced HCL burned 2.65 s of CPU and retained 44 MB, against 1.2 ms for 54 KB of well-formed
HCL. `POST /v1/imports/terraform` accepts 2 MiB, needs no credential on the default posture, and
runs the parse synchronously inside an `async def` handler, so the burn blocks the event loop
rather than one request: end to end, one 54 KB upload held `GET /health` for 2.3 s.

The fix is to end an unclosed block where the next header begins. That is what a missing brace
means to the person who wrote the file, it keeps every resource the file declares, and it confines
each body to its own resource — which is what makes the ingress hint answer for the right one.
"""

from __future__ import annotations

from otm_artifact_import.terraform_import import _iter_resource_blocks, import_terraform_text


def _internet_facing(text: str) -> list[str]:
    result = import_terraform_text(text, filename="main.tf")
    return sorted(c.id for c in result.document.components if c.in_trust_boundary == "tb_internet_facing")


def _lbs(*, first_closes: bool) -> str:
    """Five load balancers. Only the last is open to the world; the first is explicitly internal."""
    opening = 'resource "aws_lb" "lb0" {\n  internal = true\n' + ("}\n" if first_closes else "")
    middle = "".join(f'resource "aws_lb" "lb{i}" {{\n  internal = true\n}}\n' for i in (1, 2, 3))
    exposed = 'resource "aws_lb" "lb4" {\n  cidr_blocks = ["0.0.0.0/0"]\n}\n'
    return opening + middle + exposed


def _unclosed(headers: int) -> str:
    return "".join(f'resource "aws_s3_bucket" "n{i}" {{\n' for i in range(headers))


def test_an_open_cidr_marks_only_the_resource_that_declares_it() -> None:
    """The baseline the bug is measured against: with the braces balanced, the answer is right."""
    assert _internet_facing(_lbs(first_closes=True)) == ["aws_lb_lb4", "ext_clients_terraform"]


def test_a_missing_brace_does_not_make_an_internal_resource_internet_facing() -> None:
    """`lb0` says `internal = true`. No typo elsewhere in the file may contradict it."""
    assert _internet_facing(_lbs(first_closes=False)) == ["aws_lb_lb4", "ext_clients_terraform"]


def test_a_missing_brace_still_yields_every_resource_the_file_declares() -> None:
    """Refusing at the first unclosed block would cost the user four of their five resources."""
    result = import_terraform_text(_lbs(first_closes=False), filename="main.tf")
    declared = {f"aws_lb_lb{i}" for i in range(5)}

    assert declared <= {c.id for c in result.document.components}


def test_the_scanner_retains_no_more_than_the_document_it_parsed() -> None:
    """Deterministic in place of a stopwatch: the bodies are what grows, and bytes do not flake.

    Every body is a slice of the same text, so a scanner that visits each character once retains
    about one copy of the input in total. The suffix behaviour retained 800x it — 44 MB from a
    54 KB upload — which is the memory half of the same defect as the CPU burn.
    """
    text = _unclosed(1600)
    retained = sum(len(body) for _, _, body in _iter_resource_blocks(text))

    assert retained <= 2 * len(text), f"retained {retained:,} bytes from a {len(text):,} byte file"


def test_retained_bytes_grow_with_the_file_and_not_with_its_square() -> None:
    """Four times the headers may cost four times the memory, never sixteen."""
    small = sum(len(b) for _, _, b in _iter_resource_blocks(_unclosed(400)))
    large = sum(len(b) for _, _, b in _iter_resource_blocks(_unclosed(1600)))

    assert large < small * 8, f"4x the headers retained {large / small:.1f}x the bytes"


def test_a_well_formed_file_is_parsed_exactly_as_before() -> None:
    """The fix may not touch the ordinary case: same resources, same bodies, same order."""
    text = "".join(f'resource "aws_s3_bucket" "n{i}" {{\n  acl = "private"\n}}\n' for i in range(4))

    blocks = list(_iter_resource_blocks(text))

    assert [(t, n) for t, n, _ in blocks] == [("aws_s3_bucket", f"n{i}") for i in range(4)]
    assert [body.strip() for _, _, body in blocks] == ['acl = "private"'] * 4


def test_a_nested_brace_inside_a_body_does_not_end_the_block_early() -> None:
    """The brace counting still has to work: `tags = { ... }` is one block, not two."""
    text = 'resource "aws_s3_bucket" "b" {\n  tags = {\n    env = "prod"\n  }\n  acl = "private"\n}\n'

    blocks = list(_iter_resource_blocks(text))

    assert len(blocks) == 1
    assert 'acl = "private"' in blocks[0][2]
    assert 'env = "prod"' in blocks[0][2]
