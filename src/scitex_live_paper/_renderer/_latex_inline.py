"""Readable presentation of common inline LaTeX in already-escaped manuscript HTML.

The reader view of a ``.tex`` source shows text, not markup: arrows and
symbols, ``%``, thin spaces, dashes, emphasis and bold are rendered;
environments, labels, bookmarks and comments are hidden; ``\\ref`` becomes a
link to its label (named by the section heading it labels). Nothing is
executed and no macro is expanded.

Every recognised construct keeps its original text in a
``<span class="lp-tex-syntax">`` (hidden in the reader, shown by the "Show
LaTeX source" toggle) next to its rendering in a
``<span class="lp-tex-rendered">`` (hidden in source mode), so the source
view still shows the exact original line. Only text between tags is
touched: claim marks and their attributes are never rewritten. Input text is
already HTML-escaped; every output fragment is either a substring of it or a
fixed literal, so no manuscript text is unescaped.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from markupsafe import escape

__all__ = ["collect_labels", "render_inline"]

#: Symbol commands (in math or text) and what the reader sees.
_SYMBOLS = {
    "rightarrow": "→",
    "to": "→",
    "leftarrow": "←",
    "gets": "←",
    "Rightarrow": "⇒",
    "Leftarrow": "⇐",
    "leftrightarrow": "↔",
    "Leftrightarrow": "⇔",
    "mapsto": "↦",
    "uparrow": "↑",
    "downarrow": "↓",
    "times": "×",
    "pm": "±",
    "mp": "∓",
    "cdot": "·",
    "div": "÷",
    "leq": "≤",
    "le": "≤",
    "geq": "≥",
    "ge": "≥",
    "neq": "≠",
    "ne": "≠",
    "approx": "≈",
    "sim": "∼",
    "simeq": "≃",
    "equiv": "≡",
    "propto": "∝",
    "infty": "∞",
    "in": "∈",
    "notin": "∉",
    "subset": "⊂",
    "subseteq": "⊆",
    "cup": "∪",
    "cap": "∩",
    "emptyset": "∅",
    "forall": "∀",
    "exists": "∃",
    "partial": "∂",
    "nabla": "∇",
    "sum": "∑",
    "prod": "∏",
    "degree": "°",
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "epsilon": "ε",
    "varepsilon": "ε",
    "theta": "θ",
    "lambda": "λ",
    "mu": "μ",
    "pi": "π",
    "rho": "ρ",
    "sigma": "σ",
    "tau": "τ",
    "phi": "φ",
    "chi": "χ",
    "psi": "ψ",
    "omega": "ω",
    "Delta": "Δ",
    "Sigma": "Σ",
    "Omega": "Ω",
    "ldots": "…",
    "dots": "…",
    "cdots": "⋯",
    "textdegree": "°",
    "textasciitilde": "~",
    "textbackslash": "\\",
    "S": "§",
    "P": "¶",
    "copyright": "©",
    "texttimes": "×",
    "textpm": "±",
    "textmu": "µ",
}
#: Escaped punctuation commands: raw (as it appears in escaped text) -> shown.
_ESCAPES = {
    r"\%": "%",
    r"\&amp;": "&amp;",
    r"\_": "_",
    r"\#": "#",
    r"\$": "$",
    r"\{": "{",
    r"\}": "}",
    r"\,": "\u2009",
    r"\;": "\u2005",
    r"\:": "\u2005",
    r"\ ": " ",
    r"\!": "",
    r"\/": "",
    r"\\": "",
}
#: Wrapper commands rendered as an element around their (rendered) argument.
_WRAPPERS = {
    "emph": "em",
    "textit": "em",
    "textsl": "em",
    "textbf": "strong",
    "texttt": "code",
    "textsc": "span",
    "textrm": "span",
    "textsf": "span",
    "textnormal": "span",
    "underline": "u",
    "mbox": "span",
    "text": "span",
}
#: Commands with no visible output in the reader.
_SILENT = (
    "noindent",
    "maketitle",
    "centering",
    "raggedright",
    "clearpage",
    "newpage",
    "medskip",
    "smallskip",
    "bigskip",
    "par",
    "indent",
    "hfill",
    "vfill",
    "protect",
    "linebreak",
    "pagebreak",
    "newline",
)
_ENV_TITLES = {"abstract": "Abstract"}
_REFS = ("ref", "eqref", "autoref", "cref", "Cref", "nameref", "pageref")
_CITES = (
    "cite",
    "citep",
    "citet",
    "citealp",
    "citeauthor",
    "citeyear",
    "parencite",
    "textcite",
)

_ARG = r"\{((?:[^{}]|\{[^{}]*\})*)\}"
_TOKEN = re.compile(
    "|".join(
        [
            r"(?P<escape>"
            + "|".join(re.escape(k) for k in sorted(_ESCAPES, key=len, reverse=True))
            + r")",
            r"(?P<comment>(?<!\\)%.*$)",
            r"(?P<env>\\(?P<env_kind>begin|end)\s*\{(?P<env_name>[^{}]*)\}(?:\[[^\]]*\])?)",
            r"(?P<bookmark>\\pdfbookmark(?:\[[^\]]*\])?\{[^{}]*\}\{[^{}]*\})",
            r"(?P<label>\\label\s*\{(?P<label_key>[^{}]*)\})",
            r"(?P<ref>\\(?:" + "|".join(_REFS) + r")\*?\s*\{(?P<ref_key>[^{}]*)\})",
            r"(?P<cite>\\(?:"
            + "|".join(_CITES)
            + r")\*?(?:\[[^\]]*\]){0,2}\s*\{(?P<cite_keys>[^{}]*)\})",
            r"(?P<wrap>\\(?P<wrap_cmd>" + "|".join(_WRAPPERS) + r")\s*" + _ARG + r")",
            r"(?P<silent>\\(?:" + "|".join(_SILENT) + r")(?![A-Za-z]))",
            r"(?P<item>\\item(?![A-Za-z])(?:\[[^\]]*\])?)",
            r"(?P<math>(?<!\\)\$(?P<math_body>[^$]+)\$)",
            r"(?P<symbol>\\(?P<symbol_name>[A-Za-z]+)(?![A-Za-z])(?:\{\})?)",
            r"(?P<emdash>---)",
            r"(?P<endash>--)",
            r"(?P<tilde>~)",
            r"(?P<lquote>``)",
            r"(?P<rquote>&#39;&#39;)",
        ]
    )
)
_TAG = re.compile(r"(<[^>]*>)")


def _syntax(raw: str) -> str:
    return f'<span class="lp-tex-syntax">{raw}</span>'


def _shown(raw: str, rendered: str, cls: str = "") -> str:
    extra = f" {cls}" if cls else ""
    return _syntax(raw) + f'<span class="lp-tex-rendered{extra}">{rendered}</span>'


def _render_text(
    text: str, labels: Mapping[str, str | None], *, math: bool = False
) -> str:
    out: list[str] = []
    pos = 0
    for m in _TOKEN.finditer(text):
        kind = m.lastgroup
        raw = m.group(0)
        if kind in {"emdash", "endash", "tilde", "lquote", "rquote"} and math:
            continue
        piece = _token(m, raw, labels, math=math)
        if piece is None:
            continue
        out.append(text[pos : m.start()])
        out.append(piece)
        pos = m.end()
    out.append(text[pos:])
    return "".join(out)


def _token(
    m: re.Match, raw: str, labels: Mapping[str, str | None], *, math: bool
) -> str | None:
    g = m.group
    if g("escape"):
        return _shown(raw, _ESCAPES[raw])
    if g("comment"):
        return _syntax(raw)
    if g("env"):
        title = _ENV_TITLES.get(g("env_name").strip())
        if title and g("env_kind") == "begin":
            return _shown(raw, title, "lp-tex-env-title")
        return _syntax(raw)
    if g("bookmark") or g("silent"):
        return _syntax(raw)
    if g("label"):
        key = g("label_key").strip()
        return f'<span class="lp-tex-anchor" id="lp-label-{key}"></span>' + _syntax(raw)
    if g("ref"):
        key = g("ref_key").strip()
        if key in labels:
            name = labels[key] or key
            return _shown(
                raw, f'<a class="lp-tex-ref" href="#lp-label-{key}">{name}</a>'
            )
        return _shown(raw, f'<span class="lp-tex-ref-unresolved">{key}</span>')
    if g("cite"):
        keys = ", ".join(k.strip() for k in g("cite_keys").split(",") if k.strip())
        return _shown(raw, f'<span class="lp-tex-cite">[{keys}]</span>')
    if g("wrap"):
        cmd = g("wrap_cmd")
        tag = _WRAPPERS[cmd]
        inner = _render_text(
            m.group(_TOKEN.groupindex["wrap_cmd"] + 1), labels, math=math
        )
        head = raw[: raw.index("{") + 1]
        return (
            _syntax(head)
            + f'<{tag} class="lp-tex-{cmd}">{inner}</{tag}>'
            + _syntax("}")
        )
    if g("item"):
        return _shown(raw, "•\u00a0", "lp-tex-item")
    if g("math"):
        body = _render_text(g("math_body"), labels, math=True)
        return _syntax("$") + f'<span class="lp-tex-math">{body}</span>' + _syntax("$")
    if g("symbol"):
        name = g("symbol_name")
        if name not in _SYMBOLS:
            return None  # unknown command: stays literal
        return _shown(raw, _SYMBOLS[name])
    rendered = {
        "emdash": "—",
        "endash": "–",
        "tilde": "\u00a0",
        "lquote": "“",
        "rquote": "”",
    }
    return _shown(raw, rendered[m.lastgroup])


def render_inline(html: str, labels: Mapping[str, str | None] | None = None) -> str:
    """Render the common LaTeX in the text parts of escaped *html* (tags untouched)."""
    labels = labels or {}
    parts = _TAG.split(html)
    inside_syntax = 0
    out = []
    for part in parts:
        if part.startswith("<"):
            # Text inside a span already marked as source syntax (a heading's
            # \section{ ... } delimiters) is left exactly as it is.
            if part.startswith('<span class="lp-tex-syntax"'):
                inside_syntax += 1
            elif part == "</span>" and inside_syntax:
                inside_syntax -= 1
            out.append(part)
        elif part and not inside_syntax:
            out.append(_render_text(part, labels))
        else:
            out.append(part)
    return "".join(out)


_HEADING_LINE = re.compile(
    r"\\(?:title|section|subsection|subsubsection|paragraph|chapter)\*?\s*\{((?:[^{}]|\{[^{}]*\})*)\}"
)
_LABEL = re.compile(r"\\label\s*\{([^{}]*)\}")
_PLAIN = re.compile(r"\\[A-Za-z]+\*?\s*|[{}$]")


def collect_labels(texts: Iterable[str]) -> dict[str, str | None]:
    """``{label: heading title or None}`` for every ``\\label`` in *texts*.

    A label on a heading's line is
    named by that heading's title (TeX commands stripped, HTML-escaped);
    one on the next non-empty line after it too.
    """
    labels: dict[str, str | None] = {}
    for text in texts:
        heading, since = None, 99
        for line in text.splitlines():
            found = _HEADING_LINE.search(line)
            if found:
                title = _PLAIN.sub("", found.group(1)).replace("~", " ").strip()
                heading, since = (str(escape(title)) or None), 0
            for key in _LABEL.findall(line):
                labels[str(escape(key.strip()))] = heading if since <= 1 else None
            if line.strip():
                since += 0 if found else 1
    return labels
