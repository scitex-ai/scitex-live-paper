"""Readable manuscript presentation preserves source, claims and escaping."""

from copy import deepcopy

from scitex_live_paper._renderer._paper_presentation import presentation_lines
from scitex_live_paper._renderer.paper import highlight_lines


def present(text, entries=()):
    return presentation_lines(text, highlight_lines(text, list(entries)))


def test_latex_setup_is_source_only_and_title_and_section_are_headings():
    text = "\\documentclass{article}\n\\title{A readable paper}\n\\author{Researcher}\n\\begin{document}\n\\maketitle\n\\section*{Results}\nActual manuscript text.\n\\end{document}"
    rows = present(text)
    assert rows[0]["kind"] == "lp-tex-source-only"
    assert rows[1]["heading"] == 1
    assert "A readable paper" in rows[1]["html"]
    assert rows[5]["heading"] == 2
    assert str(rows[6]["html"]) == "Actual manuscript text."


def test_ordinary_text_is_not_mistaken_for_a_latex_document():
    rows = present("A plain manuscript.\nA second line.")
    assert all(row["kind"] == "" for row in rows)
    assert [str(row["html"]) for row in rows] == ["A plain manuscript.", "A second line."]


def test_claims_keep_their_original_line_anchor_value_and_verdict():
    text = "\\documentclass{article}\n\\begin{document}\nAccuracy: \\vclaim{score}.\n\\end{document}"
    entry = {"claim_id": "score", "location": {"line": 3}, "stated_text": "0.1234", "stated_value": 0.1234, "state": "not_supported", "label": "Not supported", "reason": "Different source value", "symbol": "✗"}
    before = deepcopy(entry)
    rows = present(text, [entry])
    html = str(rows[2]["html"])
    assert 'id="claim-score"' in html
    assert 'data-support="not_supported"' in html
    assert ">0.1234<sup" in html
    assert entry == before


def test_a_registered_claim_in_the_preamble_remains_visible():
    entry = {"claim_id": "setup", "location": {"line": 1}, "stated_text": "article", "state": "not_checkable", "label": "Not checkable", "reason": "Registration", "symbol": "?"}
    rows = present("\\documentclass{article}\n\\begin{document}\nText", [entry])
    assert rows[0]["kind"] != "lp-tex-source-only"
    assert 'id="claim-setup"' in rows[0]["html"]


def test_heading_text_remains_escaped_and_never_creates_untrusted_elements():
    rows = present("\\title{<img src=x onerror=alert(1)>}\n\\begin{document}\nText")
    html = str(rows[0]["html"])
    assert "&lt;img" in html and "<img" not in html
    assert html.count('class="lp-tex-syntax"') == 2


def test_graphics_source_is_preserved_without_reading_external_files():
    text = "\\begin{document}\n\\includegraphics{../../private.pdf}\n\\end{document}"
    rows = present(text)
    assert str(rows[1]["html"]) == r"\includegraphics{../../private.pdf}"
    assert rows[1]["kind"] == "lp-tex-source-only"
    assert rows[1]["figure_note"] is True
