"""The manuscript displays registered stated values without changing verdicts."""

from scitex_live_paper._renderer.paper import highlight_lines


def entry(claim_id="score.v1", value=0.91, state="supported"):
    return {
        "claim_id": claim_id,
        "location": {"line": 1},
        "stated_text": "The score is a registered claim.",
        "stated_value": value,
        "state": state,
        "source": {"value": 0.95},
        "label": state,
        "reason": "Provider verdict",
        "symbol": "✓" if state == "supported" else "✗",
    }


def test_registered_macro_displays_stated_value_with_narrow_highlight():
    # Arrange
    text = r"Accuracy is \vclaim{score.v1}; n = 20."
    # Act
    html = str(highlight_lines(text, [entry()])[0])
    # Assert
    assert (
        html.startswith("Accuracy is <mark "),
        ">0.91<sup " in html,
        html.endswith("</mark>; n = 20."),
        r"\vclaim" not in html,
    ) == (True, True, True, True)


def test_unsupported_claim_keeps_its_stated_value_and_state():
    # Arrange
    claim = entry(state="not_supported")
    # Act
    html = str(
        highlight_lines(
            r"Accuracy is \vclaim{score.v1}.",
            [
                claim,
            ],
        )[0]
    )

    # Assert
    assert (
        'data-support="not_supported"' in html,
        ">0.91<sup " in html,
        "0.95" not in html,
    ) == (True, True, True)


def test_wrapped_value_from_a_real_numeric_claim_displays_the_number():
    # Arrange
    claim = entry(value={"value": 0.91})
    # Act
    html = str(
        highlight_lines(
            r"Accuracy: \vclaim{score.v1}",
            [
                claim,
            ],
        )[0]
    )

    # Assert
    assert (">0.91<sup " in html, "{'value':" not in html) == (True, True)


def test_unregistered_macro_and_untagged_numbers_remain_unassessed():
    # Arrange
    text = r"n = 20; \vclaim{unregistered}"
    # Act
    html = str(highlight_lines(text, [])[0])
    # Assert
    assert (html, "<mark" not in html) == (text, True)


def test_registered_display_value_is_html_escaped():
    # Arrange
    claim = entry(value="<script>alert(1)</script>")
    # Act
    html = str(
        highlight_lines(
            r"Value: \vclaim{score.v1}",
            [
                claim,
            ],
        )[0]
    )

    # Assert
    assert (
        "&lt;script&gt;alert(1)&lt;/script&gt;" in html,
        "<script>" not in html,
    ) == (True, True)


def test_missing_stated_value_does_not_invent_one_from_source():
    # Arrange
    claim = entry(value=None)
    # Act
    html = str(highlight_lines(r"Value: \vclaim{score.v1}", [claim])[0])
    # Assert
    assert (r"\vclaim{score.v1}" in html, "0.95" not in html) == (True, True)
