"""Real consumer payload translation across supported port and anchor shapes."""

from __future__ import annotations
import pytest
from scitex_live_paper.ports import translate_consumer_payload


@pytest.mark.parametrize(
    "payload,expected",
    [
        (
            {"port": "figure", "target": "fig-demo-1", "options": {"size": "lg"}},
            {
                "kind": "port",
                "port": "figure",
                "target": "fig-demo-1",
                "options": {"size": "lg"},
            },
        ),
        (
            {"figure_id": "fig-demo-1"},
            {"kind": "port", "port": "figure", "target": "fig-demo-1", "options": {}},
        ),
        (
            {"claim_id": "mnist_logreg_accuracy"},
            {
                "kind": "port",
                "port": "claim-graph",
                "target": "mnist_logreg_accuracy",
                "options": {},
            },
        ),
    ],
)
def test_supported_payload_normalizes_port_action(payload, expected):
    # Arrange
    # Act
    actual = translate_consumer_payload(payload)
    # Assert
    assert actual == (expected, None)


@pytest.mark.parametrize("key", ["body", "text", "content"])
@pytest.mark.parametrize(
    "target",
    [{"claim_id": "c1"}, {"page": 3, "bbox": [1, 2, 3, 4]}, {"quote": "accuracy 0.89"}],
)
def test_comment_alias_preserves_anchor_author(key, target):
    # Arrange
    payload = {key: "check this value", "target": target, "author": "yw"}
    # Act
    action, error = translate_consumer_payload(payload)
    # Assert
    assert (error, action) == (
        None,
        {
            "kind": "comment",
            "comment": {"body": "check this value", "target": target, "author": "yw"},
        },
    )


@pytest.mark.parametrize(
    "bad", [None, [], "nope", {}, {"body": "  "}, {"port": "nope", "target": "x"}]
)
def test_invalid_payload_reports_translation_error(bad):
    # Arrange
    # Act
    action, error = translate_consumer_payload(bad)
    # Assert
    assert action is None and isinstance(error, str)
