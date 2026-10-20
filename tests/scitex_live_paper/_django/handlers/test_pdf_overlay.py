"""STX-TQ tests for the CCT 3000 PDF base layer + event overlay.

Pins the Django SPA overlay wiring: claim-anchor regions painted
over PDF.js pages from anchor bboxes (``claim-overlays.js``),
port-events bus binding + evidence popup chrome, the event-log
sidecar (``event-log.js``), and the print/export strip
(``viewer.css`` ``@media print`` hides the overlay).

All assertions are static (file text) — the JS runs in the
browser; here we pin the contract the browser relies on.
"""

from __future__ import annotations

from pathlib import Path


def _js_dir() -> Path:
    import scitex_live_paper

    pkg_root = Path(scitex_live_paper.__file__).resolve().parent
    return pkg_root / "_django/static/live_paper/js"


def _css_file() -> Path:
    import scitex_live_paper

    pkg_root = Path(scitex_live_paper.__file__).resolve().parent
    return pkg_root / "_django/static/live_paper/css/viewer.css"


def _module_file(name: str) -> Path:
    return _js_dir() / name


# ---------------------------------------------------------------------------
# Module existence
# ---------------------------------------------------------------------------


def test_claim_overlays_module_exists():
    # Arrange
    # Act
    # Assert
    assert _module_file("claim-overlays.js").is_file()


def test_event_log_module_exists():
    # Arrange
    # Act
    # Assert
    assert _module_file("event-log.js").is_file()


# ---------------------------------------------------------------------------
# claim-overlays.js contract
# ---------------------------------------------------------------------------


def test_claim_overlays_exports_group_claims_by_page():
    # Arrange
    # Act
    text = _module_file("claim-overlays.js").read_text(encoding="utf-8")
    # Assert
    assert "export function groupClaimsByPage" in text


def test_claim_overlays_exports_bbox_converter():
    # Arrange
    # Act
    text = _module_file("claim-overlays.js").read_text(encoding="utf-8")
    # Assert
    assert "export function pdfBboxToCssRect" in text
    assert "convertToViewportRectangle" in text


def test_claim_overlays_exports_painters():
    # Arrange
    # Act
    text = _module_file("claim-overlays.js").read_text(encoding="utf-8")
    # Assert
    assert "export function paintClaimAnchor" in text
    assert "export function paintPageOverlays" in text


def test_claim_overlays_binds_figure_port():
    # Arrange
    # Act
    text = _module_file("claim-overlays.js").read_text(encoding="utf-8")
    # Assert
    assert "data-lp-port" in text
    assert '"figure"' in text
    assert "data-lp-target" in text


def test_claim_overlays_maps_status_classes():
    # Arrange
    # Act
    text = _module_file("claim-overlays.js").read_text(encoding="utf-8")
    # Assert
    assert "lp-status-verified" in text
    assert "lp-status-suspect" in text


# ---------------------------------------------------------------------------
# event-log.js contract
# ---------------------------------------------------------------------------


def test_event_log_exports_sidecar_api():
    # Arrange
    # Act
    text = _module_file("event-log.js").read_text(encoding="utf-8")
    # Assert
    assert "export function createEventLog" in text
    assert "export function recordEvent" in text
    assert "export function exportSidecar" in text
    assert "export function bindEventLog" in text


def test_event_log_sidecar_schema_pinned():
    # Arrange
    # Act
    text = _module_file("event-log.js").read_text(encoding="utf-8")
    # Assert
    assert "scitex-live-paper.event-log/v1" in text


# ---------------------------------------------------------------------------
# pdf-viewer.js wiring
# ---------------------------------------------------------------------------


def test_pdf_viewer_imports_claim_overlays():
    # Arrange
    # Act
    text = _module_file("pdf-viewer.js").read_text(encoding="utf-8")
    # Assert
    assert 'from "./claim-overlays.js"' in text


def test_pdf_viewer_exposes_set_claims():
    # Arrange
    # Act
    text = _module_file("pdf-viewer.js").read_text(encoding="utf-8")
    # Assert
    assert "setClaims" in text


def test_pdf_viewer_paints_overlays_per_page():
    # Arrange
    # Act
    text = _module_file("pdf-viewer.js").read_text(encoding="utf-8")
    # Assert
    assert "paintPageOverlays" in text


# ---------------------------------------------------------------------------
# viewer.js wiring
# ---------------------------------------------------------------------------


def test_viewer_binds_port_events_bus():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert 'from "./port-events.js"' in text
    assert "bindPortEvents" in text


def test_viewer_binds_event_log():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert 'from "./event-log.js"' in text
    assert "bindEventLog" in text


def test_viewer_feeds_claims_to_pdf_viewer():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert "viewer.setClaims" in text


def test_viewer_resolves_pdfjs_from_module_url():
    # Arrange — static files sit beside the module under staticfiles;
    # the API base moves with the mount point, so it must never be
    # the PDF.js base (it built /pdfjs/... = 404).
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert "import.meta.url" in text
    assert "document.baseURI + apiBase" not in text


# ---------------------------------------------------------------------------
# viewer.css: overlay chrome + print strip
# ---------------------------------------------------------------------------


def test_css_has_overlay_layer():
    # Arrange
    # Act
    text = _css_file().read_text(encoding="utf-8")
    # Assert
    assert ".lp-overlay" in text
    assert ".lp-claim-anchor" in text


def test_css_has_evidence_popup_chrome():
    # Arrange
    # Act
    text = _css_file().read_text(encoding="utf-8")
    # Assert
    assert ".lp-evidence-popup" in text


def test_css_print_strips_overlay():
    # Arrange
    # Act
    text = _css_file().read_text(encoding="utf-8")
    # Assert
    assert "@media print" in text
    print_block = text.split("@media print", 1)[1]
    assert ".lp-overlay" in print_block
    assert ".lp-claim-anchor" in print_block
