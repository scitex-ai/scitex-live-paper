"""E2E: render the in-tree fixture bundle into a static site (PS-212).

Full workflow against the real renderer (no mocks, no patches):
subprocess-driven `render` of `bundle-min` into a tmp dir, asserting
the four emitted pages land on disk. Loopback only — no network, no
credentials.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e

FIXTURE_BUNDLE = (
    Path(__file__).resolve().parents[1] / "scitex_live_paper" / "fixtures" / "bundle-min"
)

EXPECTED_PAGES = ("index.html", "viewer.html", "claims.html", "dag.html")


def _render(bundle: Path, out_dir: Path) -> subprocess.CompletedProcess[str]:
    """Render `bundle` into `out_dir` via the real CLI subprocess."""
    return subprocess.run(
        [sys.executable, "-m", "scitex_live_paper", "render", str(bundle),
         "--out", str(out_dir)],
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )


def test_render_fixture_bundle_emits_four_pages(tmp_path):
    # Arrange
    out_dir = tmp_path / "site"
    # Act
    completed = _render(FIXTURE_BUNDLE, out_dir)
    # Assert
    assert (completed.returncode, [p for p in EXPECTED_PAGES
                                  if not (out_dir / p).is_file()]) == (0, [])


def test_render_is_idempotent(tmp_path):
    # Arrange
    out_dir = tmp_path / "site"
    first_sizes = {}
    # Act
    _render(FIXTURE_BUNDLE, out_dir)
    first_sizes = {p: (out_dir / p).stat().st_size for p in EXPECTED_PAGES}
    completed = _render(FIXTURE_BUNDLE, out_dir)
    # Assert
    assert (completed.returncode, {p: (out_dir / p).stat().st_size
                                   for p in EXPECTED_PAGES}) == (0, first_sizes)
