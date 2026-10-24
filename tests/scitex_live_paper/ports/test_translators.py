"""No-mocks tests for the consumer translator layer (prompt-10 item 6).

:func:`translate_consumer_payload` is pure — real calls, valid and
invalid shapes, no fixtures needed.
"""

from __future__ import annotations

from scitex_live_paper.ports import translate_consumer_payload


def test_explicit_port_call_passes_through():
    action, error = translate_consumer_payload(
        {"port": "figure", "target": "fig-demo-1", "options": {"size": "lg"}}
    )
    assert error is None
    assert action == {
        "kind": "port",
        "port": "figure",
        "target": "fig-demo-1",
        "options": {"size": "lg"},
    }


def test_figure_id_alias_maps_to_figure_port():
    action, error = translate_consumer_payload({"figure_id": "fig-demo-1"})
    assert error is None
    assert action is not None and action["kind"] == "port"
    assert action["port"] == "figure" and action["target"] == "fig-demo-1"


def test_bare_claim_id_is_claim_graph_lookup():
    action, error = translate_consumer_payload({"claim_id": "mnist_logreg_accuracy"})
    assert error is None
    assert action is not None and action["kind"] == "port"
    assert action["port"] == "claim-graph"


def test_comment_body_aliases_normalize():
    for key in ("body", "text", "content"):
        action, error = translate_consumer_payload(
            {key: "check this value", "target": {"claim_id": "c1"}, "author": "yw"}
        )
        assert error is None, key
        assert action is not None and action["kind"] == "comment"
        comment = action["comment"]
        assert comment["body"] == "check this value"
        assert comment["target"] == {"claim_id": "c1"}
        assert comment["author"] == "yw"


def test_region_and_quote_targets_accepted():
    action, error = translate_consumer_payload(
        {"body": "suspicious axis", "target": {"page": 3, "bbox": [1, 2, 3, 4]}}
    )
    assert error is None and action is not None and action["kind"] == "comment"
    action, error = translate_consumer_payload(
        {"body": "agrees", "target": {"quote": "accuracy 0.89"}}
    )
    assert error is None and action is not None and action["kind"] == "comment"


def test_garbage_payload_rejected():
    for bad in (None, [], "nope", {}, {"body": "  "}, {"port": "nope", "target": "x"}):
        action, error = translate_consumer_payload(bad)
        assert action is None and isinstance(error, str), bad
