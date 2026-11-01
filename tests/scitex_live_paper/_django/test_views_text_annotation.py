"""Tests for PR (c) — text-layer + annotation-layer + native Ctrl-F find.

These features close the gap writer's pdf-viewer.ts EXPLICITLY left
open (per its own docstring: "Minimal: no text-layer, no annotation-layer,
no find."). With text-layer enabled, the browser's native Ctrl-F walks
the invisible glyph spans and highlights matches — so "find" is free
once text-layer is wired.

Browser-side execution is out of pytest's scope; these tests verify
the JS / CSS source actually wires the PDF.js TextLayer +
AnnotationLayer APIs and ships the supporting CSS. The visual
verification is in the PR's manual test plan.

All collaborators are real — file IO against the installed package's
static tree. No ``monkeypatch``, no ``mock.patch``.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def _viewer_js() -> str:
    """Concatenated text of every JS module under live_paper/js/."""
    import scitex_live_paper

    pkg_root = Path(scitex_live_paper.__file__).resolve().parent
    js_dir = pkg_root / "_django/static/live_paper/js"
    return "\n".join(
        (js_dir / name).read_text(encoding="utf-8")
        for name in (
            "viewer.js",
            "pdf-viewer.js",
            "claims-sidebar.js",
            "reverify-all.js",
            "_utils.js",
        )
    )


def _viewer_css() -> str:
    import scitex_live_paper

    pkg_root = Path(scitex_live_paper.__file__).resolve().parent
    return (pkg_root / "_django/static/live_paper/css/viewer.css").read_text(
        encoding="utf-8",
    )


# The SDK now owns PDF.js raster/text/link rendering. Native LP opts in and
# consumes its own public provider; the actual rendered layers are exercised
# by check_rich_pdf_browser.py with a cropped/rotated PDF fixture.
@pytest.mark.parametrize(
    "contract",
    [
        "createRichPdfViewer",
        "textLayer: true",
        "linkLayer: true",
        "options.createPdfViewer",
    ],
)
def test_native_pdf_uses_public_provider_and_sdk_layers(contract):
    # Arrange
    expected = contract
    # Act
    source = _viewer_js()
    # Assert
    assert expected in source


def test_native_pdf_does_not_duplicate_page_renderer():
    # Arrange
    forbidden = "getTextContent"
    # Act
    source = _viewer_js()
    # Assert
    assert forbidden not in source


# ──────────────────────────────────────────────────────────────────
# CSS contract — overlays positioned + selection styled
# ──────────────────────────────────────────────────────────────────


def test_viewer_css_styles_text_layer__assert_textlayer_in_text():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert ".textLayer" in text


def test_viewer_css_styles_text_layer__assert_position_absolute_in_text():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert "position: absolute" in text


def test_viewer_css_styles_text_selection_color():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert "::selection" in text


def test_viewer_css_styles_annotation_layer_with_pointer_events_none__assert_annotationlayer_in_text():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert ".annotationLayer" in text


def test_viewer_css_styles_annotation_layer_with_pointer_events_none__assert_pointer_events_none_in_te():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert "pointer-events: none" in text


def test_viewer_css_styles_link_annotation_anchor():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert "linkAnnotation" in text


# ──────────────────────────────────────────────────────────────────
# Backward-compat regression — PR (b)'s contract still holds
# ──────────────────────────────────────────────────────────────────


def test_viewer_js_still_defines_pdfviewer_class():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "class PDFViewer" in text


def test_viewer_js_still_calls_api_pdf_endpoint():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert '"pdf?doc_type="' in text


def test_viewer_js_uses_vendored_pdfjs_bundle():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "pdf.min.mjs" in text


def test_viewer_js_still_uses_vendored_pdfjs():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert — one assertion per loop iteration: no CDN host survives
    for marker in ("cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com"):
        assert marker not in text


def test_viewer_js_still_exposes_window_pdfviewer_global():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "window.LivePaperPDFViewer" in text


def test_reverify_surfaces_failure_reason_as_tooltip():
    # Arrange — the failure reason was console-only (beta-5 gap).
    # Act
    text = _viewer_js()
    # Assert
    assert "statusBadge.title" in text


def test_reverify_all_surfaces_failure_reason_as_tooltip():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "badge.title" in text
