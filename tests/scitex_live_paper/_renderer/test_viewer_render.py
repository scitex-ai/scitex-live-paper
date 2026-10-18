"""STX-TQ tests for ``scitex_live_paper._renderer.viewer.render_viewer``.

The viewer page is a pure renderer: given a loaded :class:`Bundle` and an
output directory, it must produce ``viewer.html`` + sibling assets such
that the page opens straight from ``file://`` with no CDN. These tests
exercise the contract — what's emitted, what it links to, and the
read-only boundary with the bundle.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from scitex_live_paper import bundle as bundle_module
from scitex_live_paper._renderer import viewer as viewer_module
from scitex_live_paper._renderer.viewer import (
    PDFJS_VERSION,
    ViewerArtifacts,
    render_viewer,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
BUNDLE_MIN = FIXTURES / "bundle-min"


# ---------------------------------------------------------------------------
# Module surface
# ---------------------------------------------------------------------------


def test_module_exposes_render_viewer_callable():
    # Arrange
    target = viewer_module
    # Act
    # Assert
    assert callable(getattr(target, "render_viewer", None))


def test_module_exposes_pdfjs_version_string():
    # Arrange
    version = viewer_module.PDFJS_VERSION
    # Act
    # Assert
    assert isinstance(version, str) and version


def test_renderer_subpackage_reexports_render_viewer():
    # Arrange
    from scitex_live_paper import _renderer as renderer_pkg
    # Act
    # Assert
    assert callable(getattr(renderer_pkg, "render_viewer", None))


# ---------------------------------------------------------------------------
# Happy path on the canonical fixture
# ---------------------------------------------------------------------------


def test_render_viewer_writes_viewer_html_in_out_dir__assert_isinstance_artifacts_view(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    # Assert
    assert isinstance(artifacts, ViewerArtifacts)


def test_render_viewer_writes_viewer_html_in_out_dir__assert_artifacts_viewer_html_out(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    # Assert
    assert artifacts.viewer_html == out / "viewer.html"


def test_render_viewer_writes_viewer_html_in_out_dir__assert_artifacts_viewer_html_is(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    # Assert
    assert artifacts.viewer_html.is_file()




def test_render_viewer_copies_manuscript_pdf_alongside__assert_artifacts_manuscript_pdf(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    # Assert
    assert artifacts.manuscript_pdf == out / "manuscript.pdf"


def test_render_viewer_copies_manuscript_pdf_alongside__assert_artifacts_manuscript_pdf_2(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    # Assert
    assert artifacts.manuscript_pdf.is_file()




def test_render_viewer_copies_claims_json_alongside__assert_artifacts_claims_json_out(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    # Assert
    assert artifacts.claims_json == out / "claims.json"


def test_render_viewer_copies_claims_json_alongside__assert_artifacts_claims_json_is(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    # Assert
    assert artifacts.claims_json.is_file()




def test_render_viewer_vendors_pdfjs_main_and_worker__assert_artifacts_pdfjs_main_out(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    # Assert
    assert artifacts.pdfjs_main == out / "assets" / "pdfjs" / "pdf.min.mjs"


def test_render_viewer_vendors_pdfjs_main_and_worker__assert_artifacts_pdfjs_worker_ou(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    # Assert
    assert artifacts.pdfjs_worker == out / "assets" / "pdfjs" / "pdf.worker.min.mjs"


def test_render_viewer_vendors_pdfjs_main_and_worker__assert_artifacts_pdfjs_main_is_f(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    # Assert
    assert artifacts.pdfjs_main.is_file()


def test_render_viewer_vendors_pdfjs_main_and_worker__assert_artifacts_pdfjs_worker_is(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    # Assert
    assert artifacts.pdfjs_worker.is_file()




def test_render_viewer_vendors_css_and_js_assets__assert_artifacts_css_out_assets(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    # Assert
    assert artifacts.css == out / "assets" / "viewer.css"


def test_render_viewer_vendors_css_and_js_assets__assert_artifacts_js_out_assets_v(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    # Assert
    assert artifacts.js == out / "assets" / "viewer.js"


def test_render_viewer_vendors_css_and_js_assets__assert_artifacts_css_is_file(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    # Assert
    assert artifacts.css.is_file()


def test_render_viewer_vendors_css_and_js_assets__assert_artifacts_js_is_file(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    # Assert
    assert artifacts.js.is_file()




# ---------------------------------------------------------------------------
# Generated HTML contract
# ---------------------------------------------------------------------------


def test_viewer_html_references_local_pdf_via_data_attribute(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    html = artifacts.viewer_html.read_text(encoding="utf-8")
    # Assert: viewer hosts a relative URL → site opens from file://
    assert 'data-pdf-url="manuscript.pdf"' in html


def test_viewer_html_references_local_claims_json(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    html = artifacts.viewer_html.read_text(encoding="utf-8")
    # Assert
    assert 'data-claims-url="claims.json"' in html


def test_viewer_html_references_vendored_pdfjs_paths__assert_data_pdfjs_url_assets_pdf(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    artifacts = render_viewer(loaded, out)
    # Act
    html = artifacts.viewer_html.read_text(encoding="utf-8")
    # Assert
    assert 'data-pdfjs-url="assets/pdfjs/pdf.min.mjs"' in html


def test_viewer_html_references_vendored_pdfjs_paths__assert_data_pdfjs_worker_url_ass(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    artifacts = render_viewer(loaded, out)
    # Act
    html = artifacts.viewer_html.read_text(encoding="utf-8")
    # Assert
    assert 'data-pdfjs-worker-url="assets/pdfjs/pdf.worker.min.mjs"' in html




def test_viewer_html_loads_local_css_and_js__assert_href_assets_viewer_css_in(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    artifacts = render_viewer(loaded, out)
    # Act
    html = artifacts.viewer_html.read_text(encoding="utf-8")
    # Assert
    assert 'href="assets/viewer.css"' in html


def test_viewer_html_loads_local_css_and_js__assert_src_assets_viewer_js_in_h(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    artifacts = render_viewer(loaded, out)
    # Act
    html = artifacts.viewer_html.read_text(encoding="utf-8")
    # Assert
    assert 'src="assets/viewer.js"' in html




def test_viewer_html_embeds_pdfjs_version_in_footer(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    html = artifacts.viewer_html.read_text(encoding="utf-8")
    # Assert
    assert PDFJS_VERSION in html


def test_viewer_html_uses_default_title_when_not_provided(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    html = artifacts.viewer_html.read_text(encoding="utf-8")
    # Assert: default title contains "Live Paper"
    assert "Live Paper" in html


def test_viewer_html_honours_custom_title(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out, title="My Manuscript")
    html = artifacts.viewer_html.read_text(encoding="utf-8")
    # Assert
    assert "<title>My Manuscript</title>" in html


# ---------------------------------------------------------------------------
# Vendored JS contract — claim event channel + status colours
# ---------------------------------------------------------------------------


def test_viewer_js_dispatches_live_paper_claim_event(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    # Act
    artifacts = render_viewer(loaded, out)
    js = artifacts.js.read_text(encoding="utf-8")
    # Assert: contract with the sidebar (issue #5) — events flow through
    # a documented channel, not via direct DOM lookup.
    assert "live-paper:claim" in js


def test_viewer_js_maps_clew_status_to_css_classes__assert_lp_status_verified_in_js(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    artifacts = render_viewer(loaded, out)
    # Act
    js = artifacts.js.read_text(encoding="utf-8")
    # Assert
    assert "lp-status-verified" in js


def test_viewer_js_maps_clew_status_to_css_classes__assert_lp_status_suspect_in_js(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    artifacts = render_viewer(loaded, out)
    # Act
    js = artifacts.js.read_text(encoding="utf-8")
    # Assert
    assert "lp-status-suspect" in js


def test_viewer_js_maps_clew_status_to_css_classes__assert_lp_status_mismatch_in_js(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    artifacts = render_viewer(loaded, out)
    # Act
    js = artifacts.js.read_text(encoding="utf-8")
    # Assert
    assert "lp-status-mismatch" in js


def test_viewer_js_maps_clew_status_to_css_classes__assert_lp_status_missing_in_js(tmp_path: Path):
    # Arrange
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    artifacts = render_viewer(loaded, out)
    # Act
    js = artifacts.js.read_text(encoding="utf-8")
    # Assert
    assert "lp-status-missing" in js




# ---------------------------------------------------------------------------
# Idempotency & errors
# ---------------------------------------------------------------------------


def test_render_viewer_overwrites_existing_output_idempotently(tmp_path: Path):
    # Arrange: render once, then render again into the same dir
    loaded = bundle_module.load(BUNDLE_MIN)
    out = tmp_path / "site"
    render_viewer(loaded, out)
    # Act: second render should not raise
    artifacts = render_viewer(loaded, out, title="Run 2")
    # Assert: title from second render wins
    html = artifacts.viewer_html.read_text(encoding="utf-8")
    assert "<title>Run 2</title>" in html


def test_render_viewer_rejects_tex_only_bundle(tmp_path: Path):
    # Arrange
    bundle_dir = tmp_path / "b"
    bundle_dir.mkdir()
    (bundle_dir / "manuscript.tex").write_text(r"\documentclass{article}")
    (bundle_dir / "claims.json").write_text("[]")
    # Act
    loaded = bundle_module.load(bundle_dir)
    # Assert
    with pytest.raises(ValueError, match="PDF manuscript"):
        render_viewer(loaded, tmp_path / "site")
