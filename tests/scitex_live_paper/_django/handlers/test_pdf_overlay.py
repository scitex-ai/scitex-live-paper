"""STX-TQ tests for the CCT 3000 PDF base layer + event overlay.

Pins the Django SPA overlay wiring: claim-anchor regions painted
over PDF.js pages from anchor bboxes (``claim-overlays.js``),
port-events bus binding + evidence popup chrome, the event-log
sidecar (``event-log.js``), the viewer Archive action
(``archive.js`` — server persist with download fallback), and the
print/export strip (``viewer.css`` ``@media print`` hides the
overlay).

All assertions are static (file text) — the JS runs in the
browser; here we pin the contract the browser relies on.

One assertion per test (STX-TQ007).
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


def test_claim_overlays_uses_viewport_rectangle():
    # Arrange
    # Act
    text = _module_file("claim-overlays.js").read_text(encoding="utf-8")
    # Assert
    assert "convertToViewportRectangle" in text


def test_claim_overlays_exports_paint_claim_anchor():
    # Arrange
    # Act
    text = _module_file("claim-overlays.js").read_text(encoding="utf-8")
    # Assert
    assert "export function paintClaimAnchor" in text


def test_claim_overlays_exports_paint_page_overlays():
    # Arrange
    # Act
    text = _module_file("claim-overlays.js").read_text(encoding="utf-8")
    # Assert
    assert "export function paintPageOverlays" in text


def test_claim_overlays_binds_port_attribute():
    # Arrange
    # Act
    text = _module_file("claim-overlays.js").read_text(encoding="utf-8")
    # Assert
    assert "data-lp-port" in text


def test_claim_overlays_binds_figure_port():
    # Arrange
    # Act
    text = _module_file("claim-overlays.js").read_text(encoding="utf-8")
    # Assert
    assert '"figure"' in text


def test_claim_overlays_binds_target_attribute():
    # Arrange
    # Act
    text = _module_file("claim-overlays.js").read_text(encoding="utf-8")
    # Assert
    assert "data-lp-target" in text


def test_claim_overlays_maps_verified_class():
    # Arrange
    # Act
    text = _module_file("claim-overlays.js").read_text(encoding="utf-8")
    # Assert
    assert "lp-status-verified" in text


def test_claim_overlays_maps_suspect_class():
    # Arrange
    # Act
    text = _module_file("claim-overlays.js").read_text(encoding="utf-8")
    # Assert
    assert "lp-status-suspect" in text


# ---------------------------------------------------------------------------
# event-log.js contract
# ---------------------------------------------------------------------------


def test_event_log_exports_create_event_log():
    # Arrange
    # Act
    text = _module_file("event-log.js").read_text(encoding="utf-8")
    # Assert
    assert "export function createEventLog" in text


def test_event_log_exports_record_event():
    # Arrange
    # Act
    text = _module_file("event-log.js").read_text(encoding="utf-8")
    # Assert
    assert "export function recordEvent" in text


def test_event_log_exports_export_sidecar():
    # Arrange
    # Act
    text = _module_file("event-log.js").read_text(encoding="utf-8")
    # Assert
    assert "export function exportSidecar" in text


def test_event_log_exports_bind_event_log():
    # Arrange
    # Act
    text = _module_file("event-log.js").read_text(encoding="utf-8")
    # Assert
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


def test_viewer_imports_port_events_module():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert 'from "./port-events.js"' in text


def test_viewer_calls_bind_port_events():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert "bindPortEvents" in text


def test_viewer_imports_event_log_module():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert 'from "./event-log.js"' in text


def test_viewer_calls_bind_event_log():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
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


def test_viewer_never_resolves_pdfjs_from_api_base():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
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


def test_css_has_claim_anchor():
    # Arrange
    # Act
    text = _css_file().read_text(encoding="utf-8")
    # Assert
    assert ".lp-claim-anchor" in text


def test_css_has_evidence_popup_chrome():
    # Arrange
    # Act
    text = _css_file().read_text(encoding="utf-8")
    # Assert
    assert ".lp-evidence-popup" in text


def test_css_print_block_exists():
    # Arrange
    # Act
    text = _css_file().read_text(encoding="utf-8")
    # Assert
    assert "@media print" in text


def test_css_print_strips_overlay_layer():
    # Arrange
    # Act
    text = _css_file().read_text(encoding="utf-8")
    # Assert
    print_block = text.split("@media print", 1)[1]
    assert ".lp-overlay" in print_block


def test_css_print_strips_claim_anchor():
    # Arrange
    # Act
    text = _css_file().read_text(encoding="utf-8")
    # Assert
    print_block = text.split("@media print", 1)[1]
    assert ".lp-claim-anchor" in print_block


# ---------------------------------------------------------------------------
# Module existence
# ---------------------------------------------------------------------------


def test_archive_module_exists():
    # Arrange
    # Act
    # Assert
    assert _module_file("archive.js").is_file()


# ---------------------------------------------------------------------------
# archive.js contract
# ---------------------------------------------------------------------------


def test_archive_exports_render_archive_button():
    # Arrange
    # Act
    text = _module_file("archive.js").read_text(encoding="utf-8")
    # Assert
    assert "export function renderArchiveButton" in text


def test_archive_exports_archive_event_log():
    # Arrange
    # Act
    text = _module_file("archive.js").read_text(encoding="utf-8")
    # Assert
    assert "export async function archiveEventLog" in text


def test_archive_uses_server_persist():
    # Arrange
    # Act
    text = _module_file("archive.js").read_text(encoding="utf-8")
    # Assert
    assert "persistSidecar" in text


def test_archive_falls_back_to_client_download():
    # Arrange
    # Act
    text = _module_file("archive.js").read_text(encoding="utf-8")
    # Assert
    assert "downloadSidecar" in text


def test_archive_imports_event_log_helpers():
    # Arrange
    # Act
    text = _module_file("archive.js").read_text(encoding="utf-8")
    # Assert
    assert 'from "./event-log.js"' in text


def test_archive_reads_session_log_lazily():
    # Arrange
    # Act
    text = _module_file("archive.js").read_text(encoding="utf-8")
    # Assert
    assert "rootEl._livePaperEventLog" in text


def test_archive_reads_stashed_bundle_lazily():
    # Arrange
    # Act
    text = _module_file("archive.js").read_text(encoding="utf-8")
    # Assert
    assert "rootEl._livePaperBundle" in text


def test_archive_button_has_button_class():
    # Arrange
    # Act
    text = _module_file("archive.js").read_text(encoding="utf-8")
    # Assert
    assert "lp-archive-button" in text


def test_archive_button_has_status_element():
    # Arrange
    # Act
    text = _module_file("archive.js").read_text(encoding="utf-8")
    # Assert
    assert "lp-archive-status" in text


def test_archive_status_is_live_region():
    # Arrange
    # Act
    text = _module_file("archive.js").read_text(encoding="utf-8")
    # Assert
    assert 'aria-live' in text


# ---------------------------------------------------------------------------
# viewer.js boot wiring
# ---------------------------------------------------------------------------


def test_viewer_imports_archive_module():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert 'from "./archive.js"' in text


def test_viewer_calls_render_archive_button():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert "renderArchiveButton" in text


def test_viewer_stashes_bundle_for_archive():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert "rootEl._livePaperBundle" in text


# ---------------------------------------------------------------------------
# viewer.css chrome + print strip
# ---------------------------------------------------------------------------


def test_css_has_archive_button_chrome():
    # Arrange
    # Act
    text = _css_file().read_text(encoding="utf-8")
    # Assert
    assert ".lp-archive-button" in text


def test_css_has_archive_status_chrome():
    # Arrange
    # Act
    text = _css_file().read_text(encoding="utf-8")
    # Assert
    assert ".lp-archive-status" in text


def test_css_print_block_exists():
    # Arrange
    # Act
    text = _css_file().read_text(encoding="utf-8")
    # Assert
    assert "@media print" in text


def test_css_print_strips_archive_button():
    # Arrange
    # Act
    text = _css_file().read_text(encoding="utf-8")
    # Assert
    print_block = text.split("@media print", 1)[1]
    assert ".lp-archive-button" in print_block


# ---------------------------------------------------------------------------
# Empty state (no paper selected)
# ---------------------------------------------------------------------------


def test_empty_state_module_exists():
    # Arrange
    # Act
    # Assert
    assert _module_file("empty-state.js").is_file()


def test_empty_state_exports_matcher():
    # Arrange
    # Act
    text = _module_file("empty-state.js").read_text(encoding="utf-8")
    # Assert
    assert "export function isMissingPaper" in text


def test_empty_state_exports_renderer():
    # Arrange
    # Act
    text = _module_file("empty-state.js").read_text(encoding="utf-8")
    # Assert
    assert "export function renderEmptyState" in text


def test_empty_state_panel_has_stable_class():
    # Arrange
    # Act
    text = _module_file("empty-state.js").read_text(encoding="utf-8")
    # Assert
    assert "lp-empty-state" in text


def test_empty_state_guides_to_working_dir():
    # Arrange
    # Act
    text = _module_file("empty-state.js").read_text(encoding="utf-8")
    # Assert
    assert "?working_dir=" in text


def test_viewer_imports_empty_state_module():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert 'from "./empty-state.js"' in text


def test_viewer_renders_empty_state_before_boot():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert "data-empty-reason" in text


def test_viewer_boot_falls_back_to_empty_state():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert "renderEmptyState(rootEl" in text


def test_fetch_json_tolerates_non_json_bodies():
    # Arrange
    # Act
    text = _module_file("_utils.js").read_text(encoding="utf-8")
    # Assert
    assert "JSON.parse(text)" in text


def test_templates_carry_empty_reason_attribute():
    # Arrange
    import scitex_live_paper

    pkg_root = Path(scitex_live_paper.__file__).resolve().parent
    standalone = (pkg_root / "_django/templates/live_paper/viewer.html").read_text(
        encoding="utf-8"
    )
    # Act
    # Assert
    assert "data-empty-reason" in standalone


def test_css_has_empty_state_chrome():
    # Arrange
    # Act
    text = _css_file().read_text(encoding="utf-8")
    # Assert
    assert ".lp-empty-state" in text


# ---------------------------------------------------------------------------
# Canonical SDK AppHeader (stats pattern — no leaf <header>)
# ---------------------------------------------------------------------------


def test_viewer_extends_sdk_app_shell():
    # Arrange
    import scitex_live_paper

    pkg_root = Path(scitex_live_paper.__file__).resolve().parent
    # Act
    text = (pkg_root / "_django/templates/live_paper/viewer.html").read_text(
        encoding="utf-8"
    )
    # Assert
    assert '{% extends "scitex_sdk/app/app_shell.html" %}' in text


def test_viewer_declares_canonical_app_header():
    # Arrange
    import scitex_live_paper

    pkg_root = Path(scitex_live_paper.__file__).resolve().parent
    # Act
    text = (pkg_root / "_django/templates/live_paper/viewer.html").read_text(
        encoding="utf-8"
    )
    # Assert
    assert "data-stx-app-header" in text


def test_viewer_mounts_sdk_app_header_component():
    # Arrange
    import scitex_live_paper

    pkg_root = Path(scitex_live_paper.__file__).resolve().parent
    # Act
    text = (pkg_root / "_django/templates/live_paper/viewer.html").read_text(
        encoding="utf-8"
    )
    # Assert
    assert "scitex_sdk/ui/js/app/app-header.js" in text


def test_viewer_renders_no_custom_h1():
    # Arrange
    import scitex_live_paper

    pkg_root = Path(scitex_live_paper.__file__).resolve().parent
    # Act
    text = (pkg_root / "_django/templates/live_paper/viewer.html").read_text(
        encoding="utf-8"
    )
    # Assert
    assert "<h1>" not in text


def test_viewer_links_sdk_app_header_stylesheet():
    # Arrange — the header JS without its stylesheet renders title
    # and version jammed together with no gap.
    import scitex_live_paper

    pkg_root = Path(scitex_live_paper.__file__).resolve().parent
    # Act
    text = (pkg_root / "_django/templates/live_paper/viewer.html").read_text(
        encoding="utf-8"
    )
    # Assert
    assert "scitex_sdk/ui/css/app/app-header.css" in text


def test_css_targets_sdk_app_header():
    # Arrange — operator rule: no accent separator under the global
    # header. The leaf neutralises the SDK AppHeader bottom border.
    # Act
    text = _css_file().read_text(encoding="utf-8")
    # Assert
    assert ".stx-app-header" in text


def test_css_neutralises_header_separator():
    # Arrange
    # Act
    text = _css_file().read_text(encoding="utf-8")
    # Assert
    assert "border-bottom: none;" in text


def test_viewer_declares_project_picker():
    # Arrange — the AppHeader project slot stays empty unless the leaf
    # supplies the picker (stats pattern).
    import scitex_live_paper

    pkg_root = Path(scitex_live_paper.__file__).resolve().parent
    # Act
    text = (pkg_root / "_django/templates/live_paper/viewer.html").read_text(
        encoding="utf-8"
    )
    # Assert
    assert "scitex_project_picker" in text


def test_viewer_moves_picker_into_header_slot():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert "movePickerIntoHeaderSlot" in text


def test_viewer_picker_targets_header_slot_class():
    # Arrange
    # Act
    text = _module_file("viewer.js").read_text(encoding="utf-8")
    # Assert
    assert "stx-app-header__slot--project-selector" in text
