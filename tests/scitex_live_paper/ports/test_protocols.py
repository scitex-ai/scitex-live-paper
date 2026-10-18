"""Tests for ``ports.protocols`` — the three injection-point contracts."""

from __future__ import annotations

from pathlib import Path

from scitex_live_paper.bundle import Bundle, load as load_bundle
from scitex_live_paper.ports import figure_fragment
from scitex_live_paper.ports.protocols import (
    CLAIM_GRAPH_PORT,
    FIGURE_PORT,
    PORT_NAMES,
    SNIPPET_PORT,
    ClaimGraphPort,
    FigurePort,
    SnippetPort,
)

FIXTURE_BUNDLE = Path(__file__).resolve().parents[1] / "fixtures" / "bundle-min"


class StaticFigure:
    """Minimal FigurePort: serves one canned SVG for any figure id."""

    def render_figure(self, bundle, figure_id, options):
        assert isinstance(bundle, Bundle)
        return figure_fragment(
            figure_id,
            "<svg></svg>",
            [{"label": "data", "href": "data.csv"}],
        )


def test_three_ports_named():
    # Arrange
    names = PORT_NAMES
    # Act
    expected = (FIGURE_PORT, SNIPPET_PORT, CLAIM_GRAPH_PORT)
    # Assert
    assert (names, set(names)) == (expected, {"figure", "snippet", "claim-graph"})


def test_adapter_satisfies_figure_protocol_structurally():
    # Arrange
    adapter = StaticFigure()
    # Act
    check = (
        isinstance(adapter, FigurePort),
        isinstance(adapter, SnippetPort),
        isinstance(adapter, ClaimGraphPort),
    )
    # Assert
    assert check == (True, False, False)


def test_render_figure_returns_json_plain_fragment():
    # Arrange
    bundle = load_bundle(FIXTURE_BUNDLE)
    # Act
    fragment = StaticFigure().render_figure(bundle, "fig1", {})
    # Assert
    assert fragment == {
        "figure_id": "fig1",
        "mime": "image/svg+xml",
        "title": "figure:fig1",
        "html": "<svg></svg>",
        "provenance": [{"label": "data", "href": "data.csv"}],
    }
