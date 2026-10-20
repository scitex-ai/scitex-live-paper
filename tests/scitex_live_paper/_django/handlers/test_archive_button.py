"""STX-TQ tests for the CCT 3000 Archive action.

Pins the viewer Archive-button wiring: the ``archive.js`` module
renders an "Archive event log" control into the viewer header that
persists the session event log server-side (``POST <apiBase>event-log``,
stored as ``live-paper-events.json``) with a client-download fallback,
so the "PDF + event-log sidecar" archive always produces a sidecar.

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


def test_archive_uses_persist_sidecar_with_download_fallback():
    # Arrange
    # Act
    text = _module_file("archive.js").read_text(encoding="utf-8")
    # Assert
    assert "persistSidecar" in text
    assert "downloadSidecar" in text
    assert 'from "./event-log.js"' in text


def test_archive_reads_session_log_lazily():
    # Arrange
    # Act
    text = _module_file("archive.js").read_text(encoding="utf-8")
    # Assert
    assert "rootEl._livePaperEventLog" in text
    assert "rootEl._livePaperBundle" in text


def test_archive_button_has_accessible_status():
    # Arrange
    # Act
    text = _module_file("archive.js").read_text(encoding="utf-8")
    # Assert
    assert "lp-archive-button" in text
    assert "lp-archive-status" in text
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
    assert ".lp-archive-status" in text


def test_css_print_strips_archive_chrome():
    # Arrange
    # Act
    text = _css_file().read_text(encoding="utf-8")
    # Assert
    assert "@media print" in text
    print_block = text.split("@media print", 1)[1]
    assert ".lp-archive-button" in print_block
