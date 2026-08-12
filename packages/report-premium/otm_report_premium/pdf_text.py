"""Degrade text the premium PDF's font cannot draw, instead of emitting a wall of black boxes.

The premium PDF is produced by xhtml2pdf/ReportLab with the built-in Type 1 fonts. Those cover
WinAnsi (cp1252) plus the Symbol and ZapfDingbats substitution sets — measured against a real
render: Greek letters, arrows, check marks, `·`, `—` and `≤` all draw; Latin Extended-A (`ā`,
`ł`), Cyrillic, CJK, Arabic, Hebrew, fullwidth forms and emoji all come out as `■`, one box per
codepoint. A CJK title therefore reached the reader as `■■■■ Payments`, and with CJK component
names the whole report became unreadable, while the Markdown export of the same model was
perfect.

**Embedding a Unicode font was considered and rejected.** No font that covers CJK + Cyrillic +
Arabic + emoji is small enough to vendor (Noto CJK alone is tens of megabytes), and the only TTF
already on disk — Bitstream Vera, shipped inside ReportLab — covers no more scripts than the
Symbol substitution already does while adding a dependency on a third-party package's private
asset path. So this module takes the documented second option: transliterate what has a Latin
equivalent, mark what does not, and let the report say so. `render_premium_html` adds a footer
line whenever anything here changed, pointing at the Markdown export, so the degradation is never
silent.

Characters the font *can* draw are returned untouched — including the ones outside cp1252 — so
this never turns a glyph that renders today into a `?`.
"""

from __future__ import annotations

import unicodedata

#: The encoding of the built-in PDF fonts (WinAnsiEncoding).
_PDF_FONT_ENCODING = "cp1252"

#: The Greek alphabet is outside WinAnsi but ReportLab draws it from the Symbol substitution
#: font — measured: `α`, `π` and `Ω` all render. Treating it as undrawable would replace working
#: glyphs with `?`.
#: Unaccented Greek capitals and lowercase only — Symbol has no accented forms, and those fold
#: onto the plain letter instead.
_SUBSTITUTED_RANGES = ((0x0391, 0x03A9), (0x03B1, 0x03C9))

#: Blocks whose punctuation has no WinAnsi equivalent and renders as a box even though it is not
#: a letter: CJK symbols/punctuation and the halfwidth/fullwidth forms.
_ALWAYS_DEGRADE_RANGES = ((0x3000, 0x303F), (0xFF00, 0xFFEF))

#: Latin letters with no canonical decomposition, so NFKD folding cannot reach ASCII on its own.
_LATIN_FALLBACKS = {
    "ĸ": "k",
    "ł": "l",
    "đ": "d",
    "ħ": "h",
    "ı": "i",
    "ŋ": "n",
    "ŧ": "t",
}

#: Cyrillic romanisation (BGN/PCGN-style, ASCII only). Uppercase forms are derived below.
_CYRILLIC_LOWER = {
    "а": "a",
    "б": "b",
    "в": "v",
    "г": "g",
    "ґ": "g",
    "д": "d",
    "е": "e",
    "ё": "yo",
    "є": "ye",
    "ж": "zh",
    "з": "z",
    "и": "i",
    "і": "i",
    "ї": "yi",
    "й": "y",
    "к": "k",
    "л": "l",
    "м": "m",
    "н": "n",
    "о": "o",
    "п": "p",
    "р": "r",
    "с": "s",
    "т": "t",
    "у": "u",
    "ф": "f",
    "х": "kh",
    "ц": "ts",
    "ч": "ch",
    "ш": "sh",
    "щ": "shch",
    "ъ": "",
    "ы": "y",
    "ь": "",
    "э": "e",
    "ю": "yu",
    "я": "ya",
}

_TRANSLITERATIONS = {
    **_LATIN_FALLBACKS,
    **{k.upper(): v.capitalize() for k, v in _LATIN_FALLBACKS.items()},
    **_CYRILLIC_LOWER,
    **{k.upper(): v.capitalize() for k, v in _CYRILLIC_LOWER.items()},
}

#: What is left when a character has neither a font glyph nor a Latin reading. One per codepoint,
#: so the reader sees that something was there — the conventional unrepresentable-character mark
#: rather than a glyph that looks like a rendering fault.
_UNREPRESENTABLE = "?"


def _in_ranges(ch: str, ranges: tuple[tuple[int, int], ...]) -> bool:
    return any(low <= ord(ch) <= high for low, high in ranges)


def _encodable(text: str) -> bool:
    try:
        text.encode(_PDF_FONT_ENCODING)
    except UnicodeEncodeError:
        return False
    return True


def _drawable(text: str) -> bool:
    """True when every character has a glyph in WinAnsi or in a substitution font."""
    return all(_encodable(ch) or _in_ranges(ch, _SUBSTITUTED_RANGES) for ch in text)


def _needs_degrading(ch: str) -> bool:
    """True only for characters the built-in fonts genuinely cannot draw.

    Symbols and punctuation that are neither WinAnsi nor substituted are still left alone —
    they are rare in model text and guessing a replacement for them would be worse than leaving
    today's behaviour — except in the CJK and fullwidth blocks, where nothing is drawable.
    """
    if _drawable(ch):
        return False
    if ord(ch) > 0xFFFF:  # astral: emoji and historic scripts, none of which have a glyph
        return True
    return ch.isalpha() or _in_ranges(ch, _ALWAYS_DEGRADE_RANGES)


def _folded(ch: str) -> str:
    """Drawable form via canonical decomposition (`ā` -> `a`, `Ｑ` -> `Q`, `ά` -> `α`), or `""`."""
    stripped = "".join(c for c in unicodedata.normalize("NFKD", ch) if not unicodedata.combining(c))
    if stripped and stripped != ch and _drawable(stripped):
        return stripped
    return ""


def _replacement(ch: str) -> str:
    if not _needs_degrading(ch):
        return ch
    return _folded(ch) or _TRANSLITERATIONS.get(ch, _UNREPRESENTABLE)


def to_pdf_font_text(text: str) -> str:
    """`text` with every undrawable character transliterated, folded or marked `?`."""
    if _encodable(text):  # the common case, and it keeps the ~400 KB logo data URI cheap
        return text
    return "".join(_replacement(ch) for ch in text)
