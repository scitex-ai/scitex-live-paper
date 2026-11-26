"""Claim values shown as the manuscript states them, compared after normalising."""

import pytest

from scitex_live_paper._renderer._values import (
    compare_values,
    display_value,
    value_presentation,
)
from scitex_live_paper.bundle import Claim


@pytest.mark.parametrize(
    ("value", "stated_text", "expected"),
    [
        ({"n": 51, "N": 51}, None, "51/51"),
        ({"correct": 476, "judged": 476}, "476/476", "476/476"),
        ({"numerator": 3, "denominator": 4}, None, "3/4"),
        ({"mean": 0.5, "sd": 0.1}, None, "mean = 0.5, sd = 0.1"),
        ({"value": 0.91}, None, "0.91"),
        (0.385, "The score is a registered claim.", "0.385"),
        (12.0, None, "12"),
        ([1, 2], None, "1, 2"),
        (None, "anything", None),
    ],
)
def test_display_value_states_the_value_as_text(value, stated_text, expected):
    # Arrange
    args = (value, stated_text)
    # Act
    shown = display_value(*args)
    # Assert
    assert (shown, "{" in (shown or "")) == (expected, False)


def test_stated_text_is_used_only_when_it_carries_every_value():
    # Arrange: the text names 476 but not 470
    value = {"correct": 476, "judged": 470}
    # Act
    shown = display_value(value, "476 of the judged claims")
    # Assert
    assert shown == "correct = 476, judged = 470"


@pytest.mark.parametrize(
    ("stated", "source", "state", "relation", "symbol"),
    [
        (476, "476", "supported", "equal", "="),
        (
            {"correct": 476, "judged": 476},
            {"correct": "476", "judged": "476"},
            "supported",
            "equal",
            "=",
        ),
        ("0.99", 0.9907407407407407, "supported", "rounded", "≈"),
        (0.92, 0.95, "supported", "provider_tolerance", "≈"),
        (3, 2, "not_supported", "differs", "≠"),
        ({"n": 51, "N": 51}, {"n": 50, "N": 51}, "not_supported", "differs", "≠"),
        ("abc", " abc ", "supported", "equal", "="),
        (1, True, "not_supported", "differs", "≠"),
    ],
)
def test_compare_values_normalises_types_and_precision(
    stated, source, state, relation, symbol
):
    # Arrange
    kwargs = {"state": state}
    # Act
    check = compare_values(stated, source, **kwargs)
    # Assert
    assert (check["relation"], check["symbol"]) == (relation, symbol)


def test_value_presentation_only_checks_a_reported_source_value():
    # Arrange
    entry = {
        "stated_value": {"correct": 476, "judged": 476},
        "stated_text": "476/476",
        "state": "supported",
        "source": {"value": None, "value_reported": False},
    }
    # Act
    shown = value_presentation(entry)
    # Assert
    assert shown == {"stated_display": "476/476", "value_check": None}


def test_claims_list_value_from_structured_claim_value_is_text():
    # Arrange
    record = {
        "claim_id": "c",
        "file_path": "a.tex",
        "claim_type": "value",
        "claim_value": {"n": 51, "N": 51},
    }
    # Act
    claim = Claim.from_dict(record)
    # Assert
    assert claim.claim_value == "51/51"
