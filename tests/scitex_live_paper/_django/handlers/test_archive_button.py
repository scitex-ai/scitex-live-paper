"""STX-TQ tests for the CCT 3000 Archive action.

Pins the viewer Archive-button wiring: the ``archive.js`` module
renders an "Archive event log" control into the viewer header that
persists the session event log server-side (``POST <apiBase>event-log``,
stored as ``live-paper-events.json``) with a client-download fallback,
so the "PDF + event-log sidecar" archive always produces a sidecar.

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
