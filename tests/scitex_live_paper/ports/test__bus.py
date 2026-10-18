"""Tests for ``ports.EventBus`` — synchronous in-process fan-out."""

from __future__ import annotations

import pytest

from scitex_live_paper.ports import Event, EventBus


def test_emit_fans_out_in_order_and_returns_count():
    # Arrange
    bus = EventBus()
    seen: list = []
    bus.subscribe("figure-refresh", lambda event: seen.append(("a", event)))
    bus.subscribe("figure-refresh", lambda event: seen.append(("b", event)))
    # Act
    count = bus.emit("figure-refresh", {"figure_id": "fig1"})
    # Assert
    assert (
        count,
        [tag for tag, _ in seen],
        [event.payload for _, event in seen],
    ) == (2, ["a", "b"], [{"figure_id": "fig1"}, {"figure_id": "fig1"}])


def test_emit_unhandled_returns_zero():
    # Arrange
    bus = EventBus()
    # Act
    count = bus.emit("evidence-request", {"target": "fig1"})
    # Assert — dispatcher uses this to 404 instead of empty popups
    assert count == 0


def test_unsubscribe_removes_subscriber():
    # Arrange
    bus = EventBus()
    seen: list = []
    unsubscribe = bus.subscribe("bundle-reloaded", seen.append)
    # Act
    unsubscribe()
    count = bus.emit("bundle-reloaded", {})
    # Assert
    assert (count, seen) == (0, [])


def test_subscriber_error_propagates():
    # Arrange
    bus = EventBus()

    def bad(event):
        raise RuntimeError("adapter blew up")

    bus.subscribe("figure-refresh", bad)
    # Act
    def act():
        bus.emit("figure-refresh", {})
    # Assert — the bus never swallows adapter errors
    with pytest.raises(RuntimeError):
        act()


def test_emitted_event_carries_kind_and_payload():
    # Arrange
    bus = EventBus()
    seen: list = []
    bus.subscribe("bundle-reloaded", seen.append)
    # Act
    bus.emit("bundle-reloaded", {"path": "/tmp/x"})
    # Assert
    assert (seen[0].kind, seen[0].payload) == (
        "bundle-reloaded",
        {"path": "/tmp/x"},
    )


def test_event_is_frozen_and_json_plain():
    # Arrange
    event = Event(kind="figure-refresh", payload={"figure_id": "fig1"})
    # Act
    check = (event.kind, dict(event.payload))
    # Assert
    assert check == ("figure-refresh", {"figure_id": "fig1"})
