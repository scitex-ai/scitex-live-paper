"""Common inline LaTeX is readable in the reader; the source view keeps the original."""

import re

from markupsafe import escape
from scitex_live_paper._renderer._latex_inline import collect_labels, render_inline
from scitex_live_paper._renderer.paper import highlight_lines

_SYNTAX = re.compile(r'<span class="lp-tex-syntax">(.*?)</span>')
_TAGS = re.compile(r"<[^>]+>")


def reader_text(html: str) -> str:
    """What the reader shows: source-only syntax removed, tags stripped."""
    return _TAGS.sub("", _SYNTAX.sub("", html))


def source_text(html: str) -> str:
    """What the source view shows: rendered parts removed, tags stripped."""
    html = re.sub(
        r'<span class="lp-tex-rendered[^"]*">.*?</span>(?=<|$|[^<])', "", html
    )
    return _TAGS.sub("", html)


LINE = (
    r"\begin{abstract} \pdfbookmark[1]{Abstract}{abstract} an input $\rightarrow$ "
    r"program, \emph{slices} of 10\,\% in 0.73--0.78~s. \noindent\textbf{Bold.} "
    r"See Section~\ref{sec:e1} \label{sec:intro} \end{abstract}"
)


def test_reader_renders_symbols_dashes_emphasis_and_hides_setup():
    # Arrange
    labels = collect_labels([r"\section{Captured triplets}" + "\n" + r"\label{sec:e1}"])
    # Act
    html = render_inline(str(escape(LINE)), labels)
    shown = reader_text(html)
    # Assert
    assert (
        "\\" in shown,
        "$" in shown,
        "~" in shown,
        "--" in shown,
        "Abstract" in shown,
        "input → program" in shown,
        "10 %" in shown,
        "0.73–0.78 s" in shown,
        '<em class="lp-tex-emph">slices</em>' in html,
        '<strong class="lp-tex-textbf">Bold.</strong>' in html,
        '<a class="lp-tex-ref" href="#lp-label-sec:e1">Captured triplets</a>' in html,
        'id="lp-label-sec:intro"' in html,
    ) == (False, False, False, False, True, True, True, True, True, True, True, True)


def test_source_view_keeps_every_original_character():
    # Arrange
    escaped = str(escape(LINE))
    # Act
    html = render_inline(escaped, {"sec:e1": "Captured triplets"})
    original = "".join(_SYNTAX.findall(html))
    # Assert: every recognised construct keeps its raw text for the toggle
    assert all(
        raw in original
        for raw in (
            r"\begin{abstract}",
            r"\pdfbookmark[1]{Abstract}{abstract}",
            r"$",
            r"\rightarrow",
            r"\emph{",
            r"\,",
            r"\%",
            "--",
            "~",
            r"\noindent",
            r"\label{sec:intro}",
            r"\ref{sec:e1}",
            r"\end{abstract}",
        )
    )


def test_unknown_commands_and_unresolved_refs_stay_visible():
    # Arrange
    text = str(escape(r"\foo{x} and \ref{fig:missing}"))
    # Act
    shown = reader_text(render_inline(text, {}))
    # Assert
    assert ("\\foo{x}" in shown, "fig:missing" in shown) == (True, True)


def test_claim_marks_are_not_rewritten():
    # Arrange
    entry = {
        "claim_id": "e3",
        "location": {"line": 1},
        "stated_text": "476/476",
        "stated_value": {"correct": 476, "judged": 476},
        "state": "supported",
        "label": "Supported -- by evidence",
        "reason": "value~checks",
        "symbol": "✓",
    }
    line = highlight_lines(r"reported \vclaim{e3} of the claims~--- all", [entry])[0]
    # Act
    html = render_inline(str(line))
    # Assert: attributes untouched, value as stated, text around rendered
    assert (
        'title="Supported -- by evidence: value~checks"' in html,
        ">476/476<sup" in html,
        "{'correct'" in html,
        "claims — all" in reader_text(html),
    ) == (True, True, False, True)
