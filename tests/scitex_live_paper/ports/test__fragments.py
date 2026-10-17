"""Tests for ``ports`` fragment envelopes — provenance is mandatory."""

from __future__ import annotations

import pytest

from scitex_live_paper.ports import ProvenanceLink, figure_fragment, popup_fragment


def test_popup_fragment_envelope_shape():
    # Arrange
    link = ProvenanceLink(label="code", href="plot.py")
    # Act
    fragment = popup_fragment("fig1", "<p>evidence</p>", [link])
    # Assert
    assert fragment == {
        "title": "fig1",
        "html": "<p>evidence</p>",
        "provenance": [{"label": "code", "href": "plot.py"}],
    }


def test_popup_fragment_accepts_plain_mappings():
    # Arrange
    provenance = [{"label": "data", "href": "data.csv"}]
    # Act
    fragment = popup_fragment("fig1", "<p>evidence</p>", provenance)
    # Assert
    assert fragment["provenance"] == [{"label": "data", "href": "data.csv"}]


def test_popup_fragment_rejects_empty_provenance():
    # Arrange
    title, html, provenance = "fig1", "<p>evidence</p>", []
    # Act
    def act():
        popup_fragment(title, html, provenance)
    # Assert — a fragment without provenance is a bug
    with pytest.raises(ValueError):
        act()


def test_figure_fragment_envelope_shape():
    # Arrange
    provenance = [{"label": "data", "href": "data.csv"}]
    # Act
    fragment = figure_fragment("fig1", "<svg></svg>", provenance)
    # Assert
    assert fragment == {
        "figure_id": "fig1",
        "mime": "image/svg+xml",
        "title": "figure:fig1",
        "html": "<svg></svg>",
        "provenance": [{"label": "data", "href": "data.csv"}],
    }
