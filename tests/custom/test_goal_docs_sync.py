"""Regression locks for the /goal docs sync (M3 shipped + fixture move).

README and the dev docs drifted while the leaf shipped 0.2.x: M3 went
from "in flight (hub-side)" to deployed at `/apps/live-paper/`, the
`serve` command moved onto the SDK workspace shell (`[server]`
extra), and fixtures moved to `tests/scitex_live_paper/fixtures/`.
These pins fail the moment prose and source disagree again.

Real file IO — no mocks, no monkeypatch. STX-TQ single-assert.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


# ──────────────────────────────────────────────────────────────────
# README marks M3 shipped at the real mount point
# ──────────────────────────────────────────────────────────────────


def test_readme_marks_m3_shipped():
    # Arrange
    # Act
    text = _read("README.md")
    # Assert
    assert "| M3 | shipped |" in text


def test_readme_mounts_at_apps_live_paper():
    # Arrange
    # Act
    text = _read("README.md")
    # Assert
    assert "/apps/live-paper/" in text


def test_readme_no_longer_names_viewer_v2():
    # Arrange
    # Act
    text = _read("README.md")
    # Assert
    assert "/viewer-v2/" not in text


# ──────────────────────────────────────────────────────────────────
# README CLI section matches the serve/mcp/ports surface
# ──────────────────────────────────────────────────────────────────


def test_readme_serve_names_server_extra():
    # Arrange
    # Act
    text = _read("README.md")
    # Assert
    assert "`[server]`" in text


def test_readme_extras_matrix_names_server():
    # Arrange
    # Act
    text = _read("README.md")
    # Assert
    assert "| `server` |" in text


def test_readme_names_entry_point_group():
    # Arrange
    # Act
    text = _read("README.md")
    # Assert
    assert "scitex.livepaper.renderers" in text


# ──────────────────────────────────────────────────────────────────
# Quickstart paths exist on disk
# ──────────────────────────────────────────────────────────────────


def test_quickstart_fixture_path_exists():
    # Arrange
    # Act
    fixture = ROOT / "tests/scitex_live_paper/fixtures/bundle-min"
    # Assert
    assert fixture.is_dir()


def test_quickstart_names_no_stale_fixture_root():
    # Arrange
    # Act
    text = _read("docs/dev-quickstart.md")
    # Assert
    assert "tests/fixtures/" not in text


def test_quickstart_names_cli_package_not_module():
    # Arrange
    # Act
    text = _read("docs/dev-quickstart.md")
    # Assert
    assert "`src/scitex_live_paper/_cli/`" in text


def test_quickstart_django_skeleton_landed():
    # Arrange
    # Act
    text = _read("docs/dev-quickstart.md")
    # Assert
    assert "issue #8" not in text


# ──────────────────────────────────────────────────────────────────
# API-consistency rule doc tracks the surfaces it governs
# ──────────────────────────────────────────────────────────────────


def test_api_consistency_doc_exists():
    # Arrange
    # Act
    doc = ROOT / "docs/dev/api-consistency.md"
    # Assert
    assert doc.is_file()


def test_api_consistency_doc_names_registry_and_tool_funcs():
    # Arrange
    # Act
    text = _read("docs/dev/api-consistency.md")
    # Assert
    assert "HANDLERS" in text and "_TOOL_FUNCS" in text


# ──────────────────────────────────────────────────────────────────
# Runbook + demo notes track the same fixture move
# ──────────────────────────────────────────────────────────────────


def test_runbook_bundle_dir_exists_on_disk():
    # Arrange
    # Act
    bundle = ROOT / "tests/scitex_live_paper/fixtures/bundle-accepted"
    # Assert
    assert bundle.is_dir()


def test_runbook_names_no_stale_fixture_root():
    # Arrange
    # Act
    text = _read("docs/dev/m2-reverify-runbook.md")
    # Assert
    assert "tests/fixtures/" not in text


def test_demo_readme_no_coming_soon():
    # Arrange
    # Act
    text = _read("docs/demo/README.md")
    # Assert
    assert "Coming Soon" not in text


# ──────────────────────────────────────────────────────────────────
# Runtime artifacts stay out of the tree (reproducibility)
# ──────────────────────────────────────────────────────────────────


def test_archive_sidecar_is_gitignored():
    # Arrange — the Archive action persists live-paper-events.json next
    # to the served bundle; live runs must not dirty the checkout.
    # Act
    text = _read(".gitignore")
    # Assert
    assert "live-paper-events.json" in text


def test_no_archive_sidecar_committed_in_fixtures():
    # Arrange
    # Act
    sidecars = list(
        (ROOT / "tests/scitex_live_paper/fixtures").rglob(
            "live-paper-events.json"
        )
    )
    # Assert
    assert sidecars == []


# ──────────────────────────────────────────────────────────────────
# Beta rule docs track the beta batch (R7 living doc)
# ──────────────────────────────────────────────────────────────────


def test_quickstart_maps_spa_js_modules():
    # Arrange
    # Act
    text = _read("docs/dev-quickstart.md")
    # Assert
    assert "live_paper/js" in text


def test_api_consistency_doc_declares_extras_fallback_rule():
    # Arrange
    # Act
    text = _read("docs/dev/api-consistency.md")
    # Assert
    assert "pickAnchor" in text


def test_api_consistency_doc_declares_sidecar_rule():
    # Arrange
    # Act
    text = _read("docs/dev/api-consistency.md")
    # Assert
    assert "live-paper-events.json" in text


def test_quickstart_notes_http_for_live_viewer():
    # Arrange
    # Act
    text = _read("docs/dev-quickstart.md")
    # Assert
    assert "http.server" in text
