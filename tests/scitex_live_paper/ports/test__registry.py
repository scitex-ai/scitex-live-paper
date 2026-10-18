"""Tests for ``ports.Registry`` — per-instance, fail-loud port mapping."""

from __future__ import annotations

import pytest

from scitex_live_paper.ports import PortNotFound, Registry, figure_fragment


class StaticFigure:
    """Minimal figure adapter for registry tests."""

    def render_figure(self, bundle, figure_id, options):
        return figure_fragment(
            figure_id, "<svg></svg>", [{"label": "data", "href": "data.csv"}]
        )


def test_registry_resolves_default_name():
    # Arrange
    registry = Registry()
    # Act
    registry.register("figure", StaticFigure())
    resolved = registry.resolve("figure")
    # Assert
    assert (isinstance(resolved, StaticFigure), registry.ports) == (True, ("figure",))


def test_registry_rejects_unknown_port():
    # Arrange
    registry = Registry()
    # Act
    def act():
        registry.register("nightmare", StaticFigure())
    # Assert — unknown port name is a packaging bug, shout
    with pytest.raises(KeyError):
        act()


def test_registry_rejects_duplicate_registration():
    # Arrange
    registry = Registry()
    registry.register("figure", StaticFigure())
    # Act
    def act():
        registry.register("figure", StaticFigure())
    # Assert — two adapters, one name: packaging bug, shout
    with pytest.raises(KeyError):
        act()


def test_registry_missing_resolve_is_port_not_found_keyerror():
    # Arrange
    registry = Registry()
    # Act
    def act():
        return registry.resolve("figure")
    # Assert
    with pytest.raises(PortNotFound):
        act()


def test_port_not_found_is_a_keyerror():
    # Arrange
    _ = Registry()
    # Act
    check = issubclass(PortNotFound, KeyError)
    # Assert
    assert check is True


def test_registries_do_not_share_state():
    # Arrange
    first, second = Registry(), Registry()
    # Act
    first.register("figure", StaticFigure())
    # Assert — per serve/render instance, never global
    assert (first.ports, second.ports) == (("figure",), ())
