"""No-mocks tests: static export mounts the canonical SDK AppHeader.

Operator header-parity rule (2026-10-22 standing orders, live-paper
Shared): the app header must be the one from scitex-sdk — never a custom
duplicate. The four static pages (index / viewer / claims / dag) used to
render their own ``<header class="live-paper-header"><h1>``; they now
mount ``[data-stx-app-header]`` (stats pattern) with the SDK CSS/JS
vendored into the site so the component works from ``file://``.

All collaborators are real: on-disk fixture (``bundle-min``), real
``bundle.load()``, real Jinja2 render, real copied SDK assets.
"""

from __future__ import annotations

from pathlib import Path

from scitex_live_paper import bundle as bundle_module
from scitex_live_paper._renderer.claims import render_claims_sidebar
from scitex_live_paper._renderer.dag import render_dag
from scitex_live_paper._renderer.index import render_index
from scitex_live_paper._renderer.viewer import render_viewer

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
BUNDLE_MIN = FIXTURES / "bundle-min"


def _render_all(tmp_path: Path, **kwargs):
    """Render the four static pages; return {name: html}."""
    loaded = bundle_module.load(BUNDLE_MIN)
    site = tmp_path / "site"
    pages = {}
    pages["index"] = render_index(loaded, site, **kwargs).index_html.read_text(
        encoding="utf-8"
    )
    pages["viewer"] = render_viewer(loaded, site, **kwargs).viewer_html.read_text(
        encoding="utf-8"
    )
    pages["claims"] = render_claims_sidebar(
        loaded, site, **kwargs
    ).claims_html.read_text(encoding="utf-8")
    pages["dag"] = render_dag(loaded, site, **kwargs).dag_html.read_text(
        encoding="utf-8"
    )
    return site, pages


import pytest


@pytest.mark.parametrize("page", ["index", "viewer", "claims", "dag"])
@pytest.mark.parametrize(
    "marker",
    [
        "data-stx-app-header",
        'data-app-title="SciTeX Live Paper"',
        'data-app-version="',
        'href="assets/sdk-app-header.css"',
        'src="assets/sdk-app-header.js"',
        'src="assets/sdk-header-slot.js"',
    ],
)
def test_exported_page_mounts_sdk_header(tmp_path, page, marker):
    # Arrange
    # Act
    _, pages = _render_all(tmp_path)
    # Assert
    assert marker in pages[page]


@pytest.mark.parametrize(
    "asset", ["sdk-app-header.css", "sdk-app-header.js", "sdk-header-slot.js"]
)
def test_sdk_assets_copied_into_site(tmp_path, asset):
    # Arrange
    # Act
    site, _ = _render_all(tmp_path)
    # Assert
    assert (site / "assets" / asset).is_file()


def test_copied_sdk_styles_define_header(tmp_path):
    # Arrange
    # Act
    site, _ = _render_all(tmp_path)
    css = (site / "assets/sdk-app-header.css").read_text()
    # Assert
    assert "stx-app-header" in css


@pytest.mark.parametrize("page", ["index", "viewer", "claims", "dag"])
@pytest.mark.parametrize("marker", ["live-paper-header", "live-paper-title", "<h1"])
def test_exported_page_avoids_duplicate_header(tmp_path, page, marker):
    # Arrange
    # Act
    _, pages = _render_all(tmp_path)
    # Assert
    assert marker not in pages[page]


@pytest.mark.parametrize(
    "page,subtitle",
    [
        ("viewer", "claim anchors overlay"),
        ("claims", "status colours"),
        ("dag", "provenance graph"),
        ("index", "opens from file://"),
    ],
)
def test_page_subtitle_stays_inside_main(tmp_path, page, subtitle):
    # Arrange
    # Act
    _, pages = _render_all(tmp_path)
    main = pages[page].split("<main")[1].split("</main>")[0]
    # Assert
    assert subtitle in main and "live-paper-subtitle" in main


@pytest.mark.parametrize("page", ["index", "viewer", "claims", "dag"])
@pytest.mark.parametrize(
    "marker",
    [
        "data-lp-static-project",
        "example-project-mnist",
        'class="lp-static-header-fallback"',
        "SciTeX Live Paper · example-project-mnist",
    ],
)
def test_project_label_renders_static_fallback(tmp_path, page, marker):
    # Arrange
    # Act
    _, pages = _render_all(tmp_path, project_label="example-project-mnist")
    # Assert
    assert marker in pages[page]


@pytest.mark.parametrize("page", ["index", "viewer", "claims", "dag"])
def test_missing_project_leaves_slot_empty(tmp_path, page):
    # Arrange
    # Act
    _, pages = _render_all(tmp_path)
    # Assert
    assert "data-lp-static-project" not in pages[page]


@pytest.mark.parametrize("asset", ["index.css", "viewer.css", "claims.css", "dag.css"])
def test_sdk_mount_hides_static_fallback(tmp_path, asset):
    # Arrange
    # Act
    site, _ = _render_all(tmp_path)
    css = (site / "assets" / asset).read_text()
    # Assert
    assert "[data-stx-app-header-mounted] .lp-static-header-fallback" in css
