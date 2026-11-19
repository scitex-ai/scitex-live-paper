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
    html = str(highlight_lines(r"Accuracy is \vclaim{score.v1}; n = 20.", [entry()])[0])

    assert html.startswith("Accuracy is <mark ")
    assert ">0.91<sup " in html
    assert html.endswith("</mark>; n = 20.")
    assert r"\vclaim" not in html


def test_unsupported_claim_keeps_its_stated_value_and_state():
    html = str(
        highlight_lines(
            r"Accuracy is \vclaim{score.v1}.",
            [
                entry(state="not_supported"),
            ],
        )[0]
    )

    assert 'data-support="not_supported"' in html
    assert ">0.91<sup " in html
    assert "0.95" not in html


def test_wrapped_value_from_a_real_numeric_claim_displays_the_number():
    html = str(
        highlight_lines(
            r"Accuracy: \vclaim{score.v1}",
            [
                entry(value={"value": 0.91}),
            ],
        )[0]
    )

    assert ">0.91<sup " in html
    assert "{'value':" not in html


def test_unregistered_macro_and_untagged_numbers_remain_unassessed():
    html = str(highlight_lines(r"n = 20; \vclaim{unregistered}", [])[0])

    assert html == r"n = 20; \vclaim{unregistered}"
    assert "<mark" not in html


def test_registered_display_value_is_html_escaped():
    html = str(
        highlight_lines(
            r"Value: \vclaim{score.v1}",
            [
                entry(value="<script>alert(1)</script>"),
            ],
        )[0]
    )

    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<script>" not in html


def test_missing_stated_value_does_not_invent_one_from_source():
    html = str(highlight_lines(r"Value: \vclaim{score.v1}", [entry(value=None)])[0])

    assert r"\vclaim{score.v1}" in html
    assert "0.95" not in html
