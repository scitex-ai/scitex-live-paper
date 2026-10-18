"""Asset-content tests for the SPA boot wiring of ``api/dashboard``.

PR-merged with PR #42 (which added the endpoint), this PR wires
``viewer.js`` to prefer the merged endpoint at boot, falling back to
the 3-call path if it 404s. Tests verify the JS source actually
implements the prefer/fallback contract — browser execution is out
of pytest's scope; visual verification is in the manual test plan.

Real file IO — no mocks.
"""

from __future__ import annotations

from pathlib import Path


def _module(name: str) -> str:
    import scitex_live_paper

    pkg_root = Path(scitex_live_paper.__file__).resolve().parent
    return (pkg_root / "_django/static/live_paper/js" / name).read_text(
        encoding="utf-8",
    )


# ──────────────────────────────────────────────────────────────────
# _utils.js — new fetchOrNull helper
# ──────────────────────────────────────────────────────────────────


def test_utils_exports_fetch_or_null():
    # Arrange
    # Act
    text = _module("_utils.js")
    # Assert
    assert "export async function fetchOrNull" in text


def test_utils_fetch_or_null_returns_null_on_non_ok():
    # Arrange
    # Act
    text = _module("_utils.js")
    # Assert
    assert "if (!res.ok) return null" in text


def test_utils_fetch_or_null_returns_null_on_network_error__assert_return_null_in_text():
    # Arrange
    # Act
    text = _module("_utils.js")
    # Assert
    assert "return null" in text


def test_utils_fetch_or_null_returns_null_on_network_error__assert_err_in_text_or_err_in_tex():
    # Arrange
    # Act
    text = _module("_utils.js")
    # Assert
    assert "(_err)" in text or "(err)" in text




# ──────────────────────────────────────────────────────────────────
# viewer.js — boot prefers dashboard, falls back on null
# ──────────────────────────────────────────────────────────────────


def test_viewer_js_imports_fetch_or_null():
    # Arrange
    # Act
    text = _module("viewer.js")
    # Assert
    assert "fetchOrNull" in text


def test_viewer_js_calls_dashboard_endpoint_first():
    # Arrange
    # Act
    text = _module("viewer.js")
    # Assert
    assert 'apiBase + "dashboard"' in text


def test_viewer_js_uses_fetch_or_null_for_dashboard():
    # Arrange
    # Act
    text = _module("viewer.js")
    # Assert
    assert 'fetchOrNull(apiBase + "dashboard")' in text


def test_viewer_js_reads_bundle_and_claims_from_dashboard__assert_dash_bundle_in_text():
    # Arrange
    # Act
    text = _module("viewer.js")
    # Assert
    assert "dash.bundle" in text


def test_viewer_js_reads_bundle_and_claims_from_dashboard__assert_dash_claims_in_text():
    # Arrange
    # Act
    text = _module("viewer.js")
    # Assert
    assert "dash.claims" in text




def test_viewer_js_falls_back_to_separate_calls_when_dashboard_missing__assert_apibase_bundle_info_in_te():
    # Arrange
    # Act
    text = _module("viewer.js")
    # Assert
    assert 'apiBase + "bundle-info"' in text


def test_viewer_js_falls_back_to_separate_calls_when_dashboard_missing__assert_apibase_claims_in_text():
    # Arrange
    # Act
    text = _module("viewer.js")
    # Assert
    assert 'apiBase + "claims"' in text




def test_viewer_js_fallback_guard_checks_bundle_and_claims_keys():
    # Arrange
    # Act
    text = _module("viewer.js")
    # Assert
    assert "dash && dash.bundle && dash.claims" in text


# ──────────────────────────────────────────────────────────────────
# Existing wiring stays — regression locks
# ──────────────────────────────────────────────────────────────────


def test_viewer_js_still_renders_re_review_badge_at_boot():
    # Arrange
    # Act
    text = _module("viewer.js")
    # Assert
    assert "renderReReviewBadge(rootEl, bundleInfo)" in text


def test_viewer_js_still_renders_claims_sidebar_when_payload_present():
    # Arrange
    # Act
    text = _module("viewer.js")
    # Assert
    assert "renderClaimsSidebar(rootEl, claimsPayload, apiBase)" in text


def test_viewer_js_still_mounts_pdf_viewer():
    # Arrange
    # Act
    text = _module("viewer.js")
    # Assert
    assert "new PDFViewer" in text


def test_viewer_js_skips_claims_render_when_payload_null():
    # Arrange
    # Act
    text = _module("viewer.js")
    # Assert
    assert "if (claimsPayload)" in text
