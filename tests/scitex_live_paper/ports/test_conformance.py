"""Tests for the consumer conformance kit + default entry-point payload."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scitex_live_paper.bundle import load as load_bundle
from scitex_live_paper.ports import (
    FigzDefaultEntry,
    FigzFigureAdapter,
    check_entry_point,
    check_figure_fragment,
)

FIXTURE_BUNDLE = Path(__file__).resolve().parents[1] / "fixtures" / "bundle-min"


def _bundle_with_figure_blob(tmp_path: Path) -> Path:
    # Arrange helper — copy bundle-min; add a figz blob + figure claim.
    overlay = tmp_path / "bundle"
    shutil.copytree(FIXTURE_BUNDLE, overlay)
    (overlay / "figz").mkdir(exist_ok=True)
    (overlay / "figz" / "fig-t1.svg").write_text(
        "<svg>test figure</svg>", encoding="utf-8"
    )
    claims_path = overlay / "claims.json"
    data = json.loads(claims_path.read_text(encoding="utf-8"))
    data["claims"].append(
        {
            "claim_id": "claim_fig_t1",
            "claim_type": "figure",
            "claim_value": "Fig T1 shows something",
            "figure_id": "fig-t1",
            "file_path": "main.tex",
            "source_session": "sess_t",
            "source_file": "scripts/03_analyze.py",
            "source_hash": "abc123",
        }
    )
    claims_path.write_text(json.dumps(data), encoding="utf-8")
    return overlay


def test_default_entry_names_figure_port():
    # Arrange
    entry = FigzDefaultEntry
    # Act
    port = entry.port
    # Assert
    assert port == "figure"


def test_default_entry_keys_default_name():
    # Arrange
    entry = FigzDefaultEntry
    # Act
    name = entry.name
    # Assert
    assert name == "default"


def test_default_entry_carries_figz_adapter():
    # Arrange
    entry = FigzDefaultEntry
    # Act
    adapter = entry.adapter
    # Assert
    assert isinstance(adapter, FigzFigureAdapter)


def test_check_entry_point_accepts_default_entry():
    # Arrange
    entry = FigzDefaultEntry
    # Act
    checked = check_entry_point(entry)
    # Assert
    assert checked == ("figure", "default", entry.adapter)


def test_check_entry_point_rejects_unknown_port():
    # Arrange
    bogus = type("Bogus", (), {"port": "nope", "adapter": object()})
    # Act + Assert
    with pytest.raises(AssertionError):
        check_entry_point(bogus)


def test_check_figure_fragment_accepts_adapter_result(tmp_path):
    # Arrange
    bundle = load_bundle(_bundle_with_figure_blob(tmp_path))
    fragment = FigzFigureAdapter().render_figure(bundle, "fig-t1", {})
    # Act
    checked = check_figure_fragment(fragment, "fig-t1")
    # Assert
    assert checked["title"] == "figure:fig-t1"


def test_check_figure_fragment_rejects_empty_provenance():
    # Arrange
    bare = {"figure_id": "x", "title": "figure:x", "html": "<svg/>", "provenance": []}
    # Act + Assert
    with pytest.raises(AssertionError):
        check_figure_fragment(bare, "x")
