"""Present common TeX structure without executing it or changing claim markup."""

from __future__ import annotations

import re
from collections.abc import Sequence

from markupsafe import Markup, escape

_HEADING = re.compile(
    r"^(\s*\\(title|author|date|section|subsection|subsubsection|paragraph)\*?\s*\{)"
    r"(.*)(\}\s*)$"
)
_LEVELS = {"title": 1, "section": 2, "subsection": 3, "subsubsection": 4, "paragraph": 5}
_BEGIN = re.compile(r"\\begin\s*\{\s*document\s*\}")
_END = re.compile(r"\\end\s*\{\s*document\s*\}")
_GRAPHICS = re.compile(r"\s*\\includegraphics(?:\[[^\]]*\])?\s*\{[^{}\r\n]*\}\s*")


def _heading_markup(raw: str, html: Markup):
    match = _HEADING.fullmatch(raw)
    if match is None:
        return None
    prefix, suffix = str(escape(match[1])), str(escape(match[4]))
    rendered = str(html)
    # Only touch literal line boundaries. Never search/replace inside a
    # generated claim's attributes or unescape manuscript-supplied HTML.
    if rendered.startswith(prefix) and rendered.endswith(suffix):
        middle = rendered[len(prefix) : -len(suffix)]
        rendered = (
            '<span class="lp-tex-syntax">' + prefix + "</span>" + middle
            + '<span class="lp-tex-syntax">' + suffix + "</span>"
        )
    return Markup(rendered), "lp-tex-" + match[2], _LEVELS.get(match[2])


def presentation_lines(text: str, highlighted: Sequence[Markup], *, is_latex=True):
    """Keep one original line/claim anchor per row, adding presentation hints.

    Source mode reveals all original escaped syntax. Reader mode hides TeX
    setup and presents common headings; unknown body commands remain literal.
    No includes, graphics, macros, scripts or external resources are executed.
    A registered claim always stays visible, including one in setup text.
    """
    has_document = bool(_BEGIN.search(text))
    inside = not has_document
    ended = False
    rows = []
    for raw, html in zip(text.splitlines(), highlighted, strict=True):
        row = {"html": html, "kind": "", "heading": None, "figure_note": False}
        if not is_latex:
            rows.append(row)
            continue
        begin, end = _BEGIN.search(raw), _END.search(raw)
        if begin:
            inside = True
        heading = _heading_markup(raw, html)
        has_claim = "<mark " in str(html)
        if heading:
            row["html"], row["kind"], row["heading"] = heading
        elif not raw.strip():
            row["kind"] = "lp-tex-paragraph"
        elif not has_claim and (
            not inside or ended or _BEGIN.fullmatch(raw.strip())
            or _END.fullmatch(raw.strip()) or raw.strip() == r"\maketitle"
            or raw.lstrip().startswith("%") or _GRAPHICS.fullmatch(raw)
        ):
            row["kind"] = "lp-tex-source-only"
            row["figure_note"] = bool(_GRAPHICS.fullmatch(raw))
        if end:
            ended = True
        rows.append(row)
    return rows
