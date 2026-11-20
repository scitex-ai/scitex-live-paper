"""Readable manuscript presentation preserves source, claims and escaping."""

from copy import deepcopy

from scitex_live_paper._renderer._paper_presentation import presentation_lines
from scitex_live_paper._renderer.paper import highlight_lines


def present(text, entries=()):
    return presentation_lines(text, highlight_lines(text, list(entries)))


def test_latex_setup_is_source_only_and_title_and_section_are_headings():
    # Arrange
    text = "\\documentclass{article}\n\\title{A readable paper}\n\\author{Researcher}\n\\begin{document}\n\\maketitle\n\\section*{Results}\nActual manuscript text.\n\\end{document}"
    # Act
    rows = present(text)
    # Assert
    assert (rows[0]["kind"], rows[1]["heading"], "A readable paper" in rows[1]["html"], rows[5]["heading"], str(rows[6]["html"])) == ("lp-tex-source-only", 1, True, 2, "Actual manuscript text.")


def test_ordinary_text_is_not_mistaken_for_a_latex_document():
    # Arrange
    text = "A plain manuscript.\nA second line."
    # Act
    rows = present(text)
    # Assert
    assert (all(row["kind"] == "" for row in rows), [str(row["html"]) for row in rows]) == (True, ["A plain manuscript.", "A second line."])


def test_claims_keep_their_original_line_anchor_value_and_verdict():
    # Arrange
    text = "\\documentclass{article}\n\\begin{document}\nAccuracy: \\vclaim{score}.\n\\end{document}"
    entry = {"claim_id": "score", "location": {"line": 3}, "stated_text": "0.1234", "stated_value": 0.1234, "state": "not_supported", "label": "Not supported", "reason": "Different source value", "symbol": "✗"}
    before = deepcopy(entry)
    # Act
    rows = present(text, [entry])
    html = str(rows[2]["html"])
    # Assert
    assert ('id="claim-score"' in html, 'data-support="not_supported"' in html, ">0.1234<sup" in html, entry == before) == (True, True, True, True)


def test_a_registered_claim_in_the_preamble_remains_visible():
    # Arrange
    entry = {"claim_id": "setup", "location": {"line": 1}, "stated_text": "article", "state": "not_checkable", "label": "Not checkable", "reason": "Registration", "symbol": "?"}
    # Act
    rows = present("\\documentclass{article}\n\\begin{document}\nText", [entry])
    # Assert
    assert (rows[0]["kind"] != "lp-tex-source-only", 'id="claim-setup"' in rows[0]["html"]) == (True, True)


def test_heading_text_remains_escaped_and_never_creates_untrusted_elements():
    # Arrange
    text = "\\title{<img src=x onerror=alert(1)>}\n\\begin{document}\nText"
    # Act
    rows = present(text)
    html = str(rows[0]["html"])
    # Assert
    assert ("&lt;img" in html, "<img" not in html, html.count('class="lp-tex-syntax"')) == (True, True, 2)


def test_graphics_source_is_preserved_without_reading_external_files():
    # Arrange
    text = "\\begin{document}\n\\includegraphics{../../private.pdf}\n\\end{document}"
    # Act
    rows = present(text)
    # Assert
    assert (str(rows[1]["html"]), rows[1]["kind"], rows[1]["figure_note"]) == (r"\includegraphics{../../private.pdf}", "lp-tex-source-only", True)
