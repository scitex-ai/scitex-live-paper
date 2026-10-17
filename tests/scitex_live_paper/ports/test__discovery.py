"""Tests for ``ports`` discovery + top-level export surface."""

from __future__ import annotations

from scitex_live_paper import ports
from scitex_live_paper.ports import EventBus, Registry, discover


def test_discover_returns_list_for_malformed_group():
    # Arrange
    group = "scitex.livepaper.renderers"
    # Act — stdlib entry points; empty group is a valid answer
    found = discover(group=group)
    # Assert
    assert isinstance(found, list)


def test_ports_visible_from_top_level_package():
    # Arrange
    import scitex_live_paper as lp

    # Act
    surface = (lp.ports, lp.ports.Registry, lp.ports.EventBus)
    # Assert
    assert surface == (ports, Registry, EventBus)
