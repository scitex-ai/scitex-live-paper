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


# ──────────────────────────────────────────────────────────────────
# SDK mount present on every page
# ──────────────────────────────────────────────────────────────────


def test_all_pages_mount_sdk_app_header(tmp_path):
    _, pages = _render_all(tmp_path)
    assert len(pages) == 4
    for name, html in pages.items():
        assert 'data-stx-app-header' in html, name
        assert 'data-app-title="SciTeX Live Paper"' in html, name
        assert 'data-app-version="' in html, name


def test_all_pages_reference_vendored_sdk_assets(tmp_path):
    _, pages = _render_all(tmp_path)
    for name, html in pages.items():
        assert 'href="assets/sdk-app-header.css"' in html, name
        assert 'src="assets/sdk-app-header.js"' in html, name
        assert 'src="assets/sdk-header-slot.js"' in html, name


def test_sdk_assets_copied_into_site(tmp_path):
    site, _ = _render_all(tmp_path)
    for rel in (
        "assets/sdk-app-header.css",
        "assets/sdk-app-header.js",
        "assets/sdk-header-slot.js",
    ):
        assert (site / rel).is_file(), rel
    css = (site / "assets" / "sdk-app-header.css").read_text(encoding="utf-8")
    assert "stx-app-header" in css


# ──────────────────────────────────────────────────────────────────
# No custom duplicate header
# ──────────────────────────────────────────────────────────────────


def test_no_custom_header_markup_on_any_page(tmp_path):
    _, pages = _render_all(tmp_path)
    for name, html in pages.items():
        assert "live-paper-header" not in html, name
        assert "live-paper-title" not in html, name
        assert "<h1" not in html, name


# ──────────────────────────────────────────────────────────────────
# Page subtitles survive inside <main>
# ──────────────────────────────────────────────────────────────────


def test_page_subtitles_live_in_main(tmp_path):
    _, pages = _render_all(tmp_path)
    assert "claim anchors overlay" in pages["viewer"]
    assert "status colours" in pages["claims"]
    assert "provenance graph" in pages["dag"]
    assert "opens from file://" in pages["index"]
    for name, html in pages.items():
        main = html.split("<main")[1].split("</main>")[0]
        assert "live-paper-subtitle" in main, name


# ──────────────────────────────────────────────────────────────────
# Project slot: static label when known, empty otherwise
# ──────────────────────────────────────────────────────────────────


def test_project_label_renders_static_slot_text(tmp_path):
    _, pages = _render_all(tmp_path, project_label="example-project-mnist")
    for name, html in pages.items():
        assert 'data-lp-static-project' in html, name
        assert "example-project-mnist" in html, name


def test_no_project_label_leaves_slot_empty(tmp_path):
    _, pages = _render_all(tmp_path)
    for name, html in pages.items():
        assert 'data-lp-static-project' not in html, name


# ──────────────────────────────────────────────────────────────────
# file:// fallback (module scripts only run over http(s))
# ──────────────────────────────────────────────────────────────────


def test_static_fallback_title_line_on_every_page(tmp_path):
    _, pages = _render_all(tmp_path, project_label="example-project-mnist")
    for name, html in pages.items():
        assert 'class="lp-static-header-fallback"' in html, name
        assert "SciTeX Live Paper · example-project-mnist" in html, name


def test_css_hides_fallback_once_sdk_mounts(tmp_path):
    site, _ = _render_all(tmp_path)
    for rel in (
        "assets/index.css",
        "assets/viewer.css",
        "assets/claims.css",
        "assets/dag.css",
    ):
        css = (site / rel).read_text(encoding="utf-8")
        assert (
            "[data-stx-app-header-mounted] .lp-static-header-fallback"
            in css
        ), rel
