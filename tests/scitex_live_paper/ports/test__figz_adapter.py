"""Tests for ``FigzFigureAdapter`` — default figure port over figz/ blobs."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scitex_live_paper.bundle import load as load_bundle
from scitex_live_paper.ports import FigzFigureAdapter, PortNotFound

FIXTURE_BUNDLE = Path(__file__).resolve().parents[1] / "fixtures" / "bundle-min"


def _bundle_with_figure_blob(tmp_path: Path) -> Path:
    """Copy bundle-min; add a figz blob + a claim carrying its figure_id."""
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


def test_figz_adapter_serves_svg_fragment(tmp_path):
    # Arrange
    bundle = load_bundle(_bundle_with_figure_blob(tmp_path))
    # Act
    fragment = FigzFigureAdapter().render_figure(bundle, "fig-t1", {})
    # Assert — envelope + SVG payload + claim provenance
    assert (
        fragment["figure_id"],
        "<svg" in fragment["html"],
        [link["label"] for link in fragment["provenance"]],
    ) == (
        "fig-t1",
        True,
        ["code: scripts/03_analyze.py", "hash: abc123"],
    )


def test_figz_adapter_unknown_figure_raises_port_not_found(tmp_path):
    # Arrange
    bundle = load_bundle(_bundle_with_figure_blob(tmp_path))
    # Act
    def act():
        FigzFigureAdapter().render_figure(bundle, "nope", {})
    # Assert — no claim carries the id → PortNotFound (→ 404)
    with pytest.raises(PortNotFound):
        act()


def test_figz_adapter_missing_blob_raises_port_not_found(tmp_path):
    # Arrange — bundle whose claim names a figure with no blob on disk
    overlay = _bundle_with_figure_blob(tmp_path)
    (overlay / "figz" / "fig-t1.svg").unlink()
    # Act
    def act():
        FigzFigureAdapter().render_figure(load_bundle(overlay), "fig-t1", {})
    # Assert — claim exists, blob gone → PortNotFound (→ 404)
    with pytest.raises(PortNotFound):
        act()
