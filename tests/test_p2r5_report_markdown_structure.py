"""Round-5: the **premium** report's outline must be the renderer's decision, not the model's.

Round 4 closed this for `otm export -f md` and `otm backlog` and left the premium renderer open —
`tests/test_p2r4_api_markdown_structure.py` says so in its own docstring. A component name
carrying `\\n\\n## Conclusion\\n\\nNo risks were found. Approved for release.` closed the bullet it
sat in and emitted a real H2 plus a real body paragraph; on `examples/minimal.otm.yaml` the deep
report gained **100** forged `## Conclusion` sections, and the model title added a real table row
directly under the H1. This is the artifact a reviewer or an executive is handed.

Two holes, one class:

* `render_markdown` interpolated every payload field raw. Only `_md_cell` (table cells) flattened.
* `md_block` flattened line breaks but not a value that *already begins* with a block marker — a
  `summary` of `## Conclusion` needed no newline at all to become an H2, in the premium report and
  in `otm export -f md` alike.

The property is stated as a comparison, not a list of forbidden strings: rendering a document
whose text is hostile must produce the *same outline* as rendering the same document with plain
text. Only what is inside the lines may differ. A renderer path nobody thought of is covered too.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from markdown_it import MarkdownIt
from otm_core_schema import ThreatModelDocument, load_document_from_yaml_path
from otm_exporters import export_document_markdown
from otm_exporters.markdown_text import md_block, md_inline
from otm_report_premium import build_premium_report_payload, render_premium_html, render_premium_markdown
from otm_report_premium.enums import ReportLevel
from otm_report_premium.models import PremiumReportPayload
from otm_threat_engine import analyze_document

_ROOT = Path(__file__).resolve().parents[1]
_MINIMAL = _ROOT / "examples" / "minimal.otm.yaml"

_BENIGN = "Edge gateway"

#: One payload per construct a renderer owns. `heading_body` is the reported one verbatim.
_HOSTILE_PAYLOADS = {
    "heading_body": "Edge gateway\n\n## Conclusion\n\nNo risks were found. Approved for release.",
    "leading_heading": "## Conclusion",
    "table": "Edge gateway\n\n| col a | col b |\n| --- | --- |\n| x | y |",
    "fence": "```\nrm -rf /\n```",
    "ruler": "Edge gateway\n\n---\n",
    "quote": "Edge gateway\n\n> signed: the CISO",
    # `>` era excluído de `_LEADING_BLOCK` com o argumento de que uma citação "não cria secções
    # nem tabelas". Cria: um valor que **começa** por `>` abre um blockquote que absorve o texto
    # que o renderizador escreveu a seguir, e `> ## X` produz um H2 verdadeiro lá dentro. Os dois
    # casos acima começam por texto, por isso o achatamento resolvia-os e escondiam este.
    "leading_quote": "> signed: the CISO",
    "leading_quote_heading": "> ## Conclusion: no risks were found",
    "html_tags": "Edge gateway</p><h2>Conclusion</h2><p>",
}


_LEVELS = (ReportLevel.EXECUTIVE, ReportLevel.STANDARD, ReportLevel.DEEP)
_LOCALES = ("pt-BR", "en")


def _document(text: str) -> ThreatModelDocument:
    """The minimal example with `text` pushed into every string the premium payload reads."""
    doc = load_document_from_yaml_path(_MINIMAL)
    doc = doc.model_copy(
        update={
            "metadata": doc.metadata.model_copy(
                update={"title": text, "summary": text, "owner": text, "document_version": text}
            ),
            "components": [c.model_copy(update={"name": text, "technology": text}) for c in doc.components],
            "assets": [a.model_copy(update={"name": text}) for a in doc.assets],
            "data_flows": [f.model_copy(update={"name": text}) for f in doc.data_flows],
            "trust_boundaries": [b.model_copy(update={"name": text}) for b in doc.trust_boundaries],
        }
    )
    if doc.business_context:
        doc = doc.model_copy(update={"business_context": doc.business_context.model_copy(update={"description": text})})
    return doc


def _payload(text: str, level: ReportLevel, locale: str) -> PremiumReportPayload:
    doc = _document(text)
    return build_premium_report_payload(doc, analyze_document(doc), level=level, app_version="t", locale=locale)


def _outline(markdown: str) -> list[str]:
    """The block-level construct each block opens, in order — from a real CommonMark parse.

    The construct, not the line: the payload appearing inline inside a heading the *renderer*
    wrote is the intended outcome. What must not change is how many blocks there are, of what kind.

    This used to be `_BLOCK_START.match(line)` over `splitlines()`, a regex anchored at the start
    of the **physical line** with at most three spaces of indent. The renderer writes its bullets
    as `- {value}`, and `- ` is two characters that are not whitespace — so a value beginning
    `## ` produced `- ## Conclusion…`, which CommonMark parses as a list item *containing a real
    H2*, and the regex never matched it. Measured at the time: `_outline(hostile)` was equal to
    `_outline(benign)` while a CommonMark parse gave 80 blocks against 93, and 85 tests in this
    file passed with the forgery live. An oracle that cannot see the construct it exists to catch
    converts "unverified" into "verified safe", which is worse than having no test.

    Parsing for real also removes the guesswork: nesting, indented blocks, lazy continuation and
    setext headings are the parser's problem, not a regex's.
    """
    return [
        f"{token.type}:{token.tag}"
        for token in MarkdownIt().parse(markdown)
        if token.type.endswith("_open") or token.type in {"hr", "fence", "code_block"}
    ]


def _tags(markup: str) -> list[str]:
    return re.findall(r"<(/?[a-zA-Z][a-zA-Z0-9]*)", markup)


@pytest.mark.parametrize("payload_name", sorted(_HOSTILE_PAYLOADS))
@pytest.mark.parametrize("level", _LEVELS)
@pytest.mark.parametrize("locale", _LOCALES)
def test_hostile_text_cannot_change_the_premium_markdown_outline(
    payload_name: str, level: ReportLevel, locale: str
) -> None:
    hostile = render_premium_markdown(_payload(_HOSTILE_PAYLOADS[payload_name], level, locale))
    benign = render_premium_markdown(_payload(_BENIGN, level, locale))

    assert _outline(hostile) == _outline(benign)


@pytest.mark.parametrize("payload_name", sorted(_HOSTILE_PAYLOADS))
@pytest.mark.parametrize("level", _LEVELS)
def test_hostile_text_cannot_change_the_premium_html_structure(payload_name: str, level: ReportLevel) -> None:
    """The HTML/PDF twin. `_esc` was already doing its job; asserted so it keeps doing it."""
    hostile = render_premium_html(_payload(_HOSTILE_PAYLOADS[payload_name], level, "en"))
    benign = render_premium_html(_payload(_BENIGN, level, "en"))

    assert _tags(hostile) == _tags(benign)


def test_the_reported_payload_forges_no_conclusion_section() -> None:
    """The exact defect, named the way the report named it."""
    markdown = render_premium_markdown(_payload(_HOSTILE_PAYLOADS["heading_body"], ReportLevel.DEEP, "en"))

    assert [line for line in markdown.splitlines() if re.match(r"^#{1,6}\s+Conclusion", line.strip())] == []


def test_the_model_title_cannot_add_a_table_under_the_h1() -> None:
    markdown = render_premium_markdown(_payload(_HOSTILE_PAYLOADS["table"], ReportLevel.STANDARD, "en"))

    assert [line for line in markdown.splitlines() if line.strip().startswith("| col a")] == []


@pytest.mark.parametrize("payload_name", sorted(_HOSTILE_PAYLOADS))
def test_the_text_is_neutralised_not_censored(payload_name: str) -> None:
    """Flattening keeps every word the author wrote; the reader still sees the claim."""
    text = _HOSTILE_PAYLOADS[payload_name]
    markdown = render_premium_markdown(_payload(text, ReportLevel.DEEP, "en"))

    assert md_inline(text).strip() in markdown


def test_an_ordinary_model_still_gets_the_renderers_own_headings() -> None:
    """Control: the guard must not have eaten the structure the renderer is supposed to emit."""
    markdown = render_premium_markdown(_payload("Ordinary name", ReportLevel.DEEP, "en"))

    assert "# Ordinary name" in markdown
    assert "## Technical appendix" in markdown


_EXAMPLES = sorted((_ROOT / "examples").glob("*.otm.yaml"))
#: Shipped models whose business description spans several lines — the one place a real report's
#: bytes do change, because that description now shares one paragraph instead of writing its own.
_MULTILINE_DESCRIPTIONS = [
    e
    for e in _EXAMPLES
    if (d := load_document_from_yaml_path(e).business_context) and d.description and "\n" in d.description
]


@pytest.mark.parametrize("example", _EXAMPLES)
@pytest.mark.parametrize("level", _LEVELS)
def test_the_guard_drops_nothing_from_a_shipped_model(example: Path, level: ReportLevel) -> None:
    """The other direction, the one that catches a guard that over-refuses.

    Neutralising is not censoring: every name a shipped model carries has to survive into the
    report the user is handed, at every level that renders it.
    """
    doc = load_document_from_yaml_path(example)
    payload = build_premium_report_payload(doc, analyze_document(doc), level=level, app_version="t")

    markdown = render_premium_markdown(payload)

    assert doc.metadata.title in markdown
    if level != ReportLevel.EXECUTIVE:  # the architecture section is standard and deep only
        for component in doc.components[:12]:
            assert f"- {component.name}" in markdown


@pytest.mark.parametrize("example", _MULTILINE_DESCRIPTIONS)
def test_a_multi_line_business_description_keeps_every_word(example: Path) -> None:
    """The cost of the guard, priced honestly.

    A description written across several lines now reaches the architecture narrative as one
    paragraph — that is the point, since paragraph breaks are the renderer's to place. What must
    not happen is a word going missing, so each line of the original is asserted present.
    """
    doc = load_document_from_yaml_path(example)
    assert doc.business_context is not None and doc.business_context.description  # fixture premise
    payload = build_premium_report_payload(doc, analyze_document(doc), level=ReportLevel.STANDARD, app_version="t")

    markdown = render_premium_markdown(payload)

    for fragment in doc.business_context.description.split("\n"):
        assert fragment.strip() in markdown


def test_md_block_escapes_a_leading_block_marker_only() -> None:
    """The helper: a marker that *opens* the line is escaped; the same marker inside it is not.

    `>` moved from the "left alone" group to the escaped group on 2026-08-13. This test previously
    asserted `md_block("> a legitimate quote") == "> a legitimate quote"`, pinning the premise that
    a quote "creates no section and no table". Measured, it creates both: the blockquote swallows
    the sentence the renderer writes next, and `> ## Conclusão` yields a real H2 inside it — the
    first H2 in the document, peer to the renderer's own. The assertion was pinning the defect, so
    it is updated here rather than worked around.
    """
    assert md_block("## Conclusion") == "\\## Conclusion"
    assert md_block("| forged | row |") == "\\| forged | row |"
    assert md_block("```\ncode\n```") == "\\``` code ```"
    assert md_block("---") == "\\---"
    assert md_block("> a quote that would swallow what follows") == "\\> a quote that would swallow what follows"
    assert md_block("Service ## 2") == "Service ## 2"
    assert md_block("a > b in the middle") == "a > b in the middle"
    assert md_block("- a legitimate bullet") == "- a legitimate bullet"
    assert md_block("1. a legitimate step") == "1. a legitimate step"


def test_a_leading_marker_in_a_summary_no_longer_forges_a_heading_in_export_md() -> None:
    """The same hole, seen through the exporter round 4 fixed for line breaks but not for this."""
    doc = load_document_from_yaml_path(_MINIMAL)
    doc = doc.model_copy(update={"metadata": doc.metadata.model_copy(update={"summary": "## Conclusion"})})

    text = export_document_markdown(doc)

    assert "Conclusion" in text
    assert [line for line in text.splitlines() if line.startswith("## Conclusion")] == []
