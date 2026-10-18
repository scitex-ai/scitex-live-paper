"""No-mocks tests for M2 follow-up — api/claims endpoint + SPA UI.

Two layers:

1. **Backend**: `api/claims` returns claim list + paper_state flags
   the SPA needs to render a Re-verify-button-aware sidebar.
2. **Frontend (asset-content level)**: viewer.js wires the sidebar +
   POST to /api/claim/verify on Re-verify button click; viewer.css
   ships the per-status colour palette.

Real Django test Client + real bundle fixtures + real file IO. No
``monkeypatch``, no ``mock.patch``.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Iterator

import pytest

pytest.importorskip("django")

from django.test import Client  # noqa: E402

from scitex_live_paper._django import services  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
BUNDLE_MIN = FIXTURES / "bundle-min"  # preprint, re_verify_enabled=False
BUNDLE_ACCEPTED = FIXTURES / "bundle-accepted"  # accepted, re_verify_enabled=True


@pytest.fixture
def env_snapshot() -> Iterator[None]:
    snap = dict(os.environ)
    try:
        yield
    finally:
        for key in list(os.environ):
            if key not in snap:
                del os.environ[key]
        for key, value in snap.items():
            os.environ[key] = value


@pytest.fixture
def client() -> Client:
    return Client()


def _pin(path: Path) -> None:
    os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = str(path)
    services.clear_cache()


# ──────────────────────────────────────────────────────────────────
# Backend: api/claims
# ──────────────────────────────────────────────────────────────────


def test_api_claims_returns_200(client, env_snapshot):
    # Arrange
    # Act
    _pin(BUNDLE_MIN)
    # Assert
    assert client.get("/api/claims").status_code == 200


def test_api_claims_returns_claim_count(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_MIN)
    # Act
    body = json.loads(client.get("/api/claims").content)
    # Assert
    assert body["claim_count"] == 3


def test_api_claims_returns_claims_array_of_correct_length__assert_isinstance_body_claims_li(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_MIN)
    # Act
    body = json.loads(client.get("/api/claims").content)
    # Assert
    assert isinstance(body["claims"], list)


def test_api_claims_returns_claims_array_of_correct_length__assert_len_body_claims_3(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_MIN)
    # Act
    body = json.loads(client.get("/api/claims").content)
    # Assert
    assert len(body["claims"]) == 3




def test_api_claims_carries_re_verify_enabled_false_for_preprint__assert_body_re_verify_enabled_is(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_MIN)
    # Act
    body = json.loads(client.get("/api/claims").content)
    # Assert
    assert body["re_verify_enabled"] is False


def test_api_claims_carries_re_verify_enabled_false_for_preprint__assert_body_pinned_commit_is_non(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_MIN)
    # Act
    body = json.loads(client.get("/api/claims").content)
    # Assert
    assert body["pinned_commit"] is None




def test_api_claims_carries_re_verify_enabled_true_for_accepted__assert_body_re_verify_enabled_is_2(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    body = json.loads(client.get("/api/claims").content)
    # Assert
    assert body["re_verify_enabled"] is True


def test_api_claims_carries_re_verify_enabled_true_for_accepted__assert_body_pinned_commit_deadbe(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    body = json.loads(client.get("/api/claims").content)
    # Assert
    assert body["pinned_commit"] == "deadbeefcafef00d12345678"




def test_api_claims_each_claim_has_required_fields(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_MIN)
    # Act
    body = json.loads(client.get("/api/claims").content)
    required = {"claim_id", "file_path", "claim_type", "status", "extras"}
    # Assert
    for claim in body["claims"]:
        missing = required - set(claim.keys())
        assert not missing, f"claim missing fields: {missing}"


def test_api_claims_preserves_clew_status_strings(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_MIN)
    body = json.loads(client.get("/api/claims").content)
    # Act
    statuses = sorted(c["status"] for c in body["claims"])
    # Assert
    assert statuses == ["registered", "suspect", "verified"]


def test_api_claims_carries_extras_for_forward_compat(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_MIN)
    body = json.loads(client.get("/api/claims").content)
    # Act
    found_extras = any(c["extras"] for c in body["claims"])
    # Assert
    assert found_extras


def test_handlers_registry_includes_api_claims():
    # Arrange
    from scitex_live_paper._django.handlers import HANDLERS, handle_claims
    # Act
    # Assert
    assert HANDLERS["api/claims"] is handle_claims


# ──────────────────────────────────────────────────────────────────
# Frontend asset content — viewer.js wires the sidebar + button
# ──────────────────────────────────────────────────────────────────


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


def test_viewer_js_fetches_api_claims_at_boot():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert 'apiBase + "claims"' in text


def test_viewer_js_has_render_claims_sidebar():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "renderClaimsSidebar" in text


def test_viewer_js_has_render_claim_row():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "renderClaimRow" in text


def test_viewer_js_has_reverify_claim_handler():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "reverifyClaim" in text


def test_viewer_js_re_verify_visibility_gated_on_re_verify_enabled():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "if (reVerifyEnabled)" in text


def test_viewer_js_reverify_posts_to_claim_verify__assert_apibase_claim_verify_in_t():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert 'apiBase + "claim/verify"' in text


def test_viewer_js_reverify_posts_to_claim_verify__assert_post_in_text_or_post_in_t():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert '"POST"' in text or "'POST'" in text




def test_viewer_js_reverify_sends_json_body_with_claim_id__assert_claim_id_claimid_in_text():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "claim_id: claimId" in text


def test_viewer_js_reverify_sends_json_body_with_claim_id__assert_json_stringify_body_in_te():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "JSON.stringify(body)" in text




def test_viewer_js_reverify_passes_pinned_commit_when_present():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "body.pinned_commit = pinnedCommit" in text


def test_viewer_js_reverify_handles_fallback_envelope():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "payload.fallback === true" in text


def test_viewer_js_reverify_shows_verifying_state_on_click__assert_verifying_in_text():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "Verifying" in text


def test_viewer_js_reverify_shows_verifying_state_on_click__assert_verifying_in_text_2():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert '"verifying"' in text




def test_viewer_js_reverify_writes_status_back_to_data_attribute__assert_rowel_dataset_status_in_t():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "rowEl.dataset.status" in text


def test_viewer_js_reverify_writes_status_back_to_data_attribute__assert_statusbadge_dataset_statu():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "statusBadge.dataset.status" in text




def test_viewer_js_reverify_handles_network_error():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "network error" in text


def test_viewer_js_reverify_re_enables_button_in_finally():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "btn.disabled = false" in text


def test_viewer_js_sidebar_uses_aside_element():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "createElement(\"aside\")" in text


def test_viewer_js_sidebar_mount_id_is_live_paper_claims():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert '"live-paper-claims"' in text


# ──────────────────────────────────────────────────────────────────
# CSS — per-status palette + the sidebar shape
# ──────────────────────────────────────────────────────────────────


def test_viewer_css_defines_status_colour_custom_properties():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    for var in (
        # clew claim-status vocabulary (verify_claim / claims.json)
        "--lp-status-verified",
        "--lp-status-suspect",
        "--lp-status-mismatch",
        "--lp-status-missing",
        "--lp-status-registered",
        "--lp-status-not_found",
        # transient client-side UI states
        "--lp-status-error",
        "--lp-status-verifying",
        # M4 re-review badge vocabulary (separate, paper-level)
        "--lp-status-stale",
        "--lp-status-contradicted",
    ):
        assert var in text, f"missing CSS custom property: {var}"


def test_viewer_css_styles_each_claim_status_via_data_attribute():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    for status in (
        "verified",
        "suspect",
        "mismatch",
        "missing",
        "registered",
        "not_found",
        "verifying",
        "error",
    ):
        assert f'.lp-claim[data-status="{status}"]' in text


def test_viewer_css_styles_claims_sidebar__assert_live_paper_claims_in_text():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert ".live-paper-claims" in text


def test_viewer_css_styles_claims_sidebar__assert_lp_claims_list_in_text():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert ".lp-claims-list" in text


def test_viewer_css_styles_claims_sidebar__assert_lp_claim_in_text():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert ".lp-claim" in text




def test_viewer_css_styles_reverify_button_disabled_state__assert_lp_claim_reverify_disable():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert ".lp-claim-reverify:disabled" in text


def test_viewer_css_styles_reverify_button_disabled_state__assert_cursor_progress_in_text():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert "cursor: progress" in text




def test_viewer_css_status_palette_uses_clew_colour_convention__assert_2ea043_in_text():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert "#2ea043" in text  # GitHub-style green


def test_viewer_css_status_palette_uses_clew_colour_convention__assert_d29922_in_text():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert "#d29922" in text  # GitHub-style amber


def test_viewer_css_status_palette_uses_clew_colour_convention__assert_f85149_in_text():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert "#f85149" in text  # GitHub-style red


def test_viewer_css_status_palette_uses_clew_colour_convention__assert_a40e26_in_text():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert "#a40e26" in text  # clew v1.3 missing-red (distinct from mismatch)




def test_viewer_css_failed_verification_renders_red_not_uncoloured__assert_re_search_r_lp_claim_data():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert re.search(
        r'\.lp-claim\[data-status="mismatch"\]\s*\{\s*'
        r"border-left-color:\s*var\(--lp-status-mismatch\)\s*;",
        text,
    )


def test_viewer_css_failed_verification_renders_red_not_uncoloured__assert_re_search_r_lp_claim_data_2():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert re.search(
        r'\.lp-claim\[data-status="missing"\]\s*\{\s*'
        r"border-left-color:\s*var\(--lp-status-missing\)\s*;",
        text,
    )


def test_viewer_css_failed_verification_renders_red_not_uncoloured__assert_re_search_r_lp_status_mis():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert re.search(r"--lp-status-mismatch:\s*#f85149\s*;", text)


def test_viewer_css_failed_verification_renders_red_not_uncoloured__assert_re_search_r_lp_status_mis_2():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert re.search(r"--lp-status-missing:\s*#a40e26\s*;", text)




# ──────────────────────────────────────────────────────────────────
# Backward-compat — PR (b) / PR (c) regressions
# ──────────────────────────────────────────────────────────────────


def test_viewer_js_still_defines_pdfviewer_class():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "class PDFViewer" in text


def test_viewer_js_still_fetches_bundle_info():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert 'apiBase + "bundle-info"' in text


def test_viewer_js_still_wires_text_layer():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "_renderTextLayer" in text


def test_viewer_js_still_wires_annotation_layer():
    # Arrange
    # Act
    text = _viewer_js()
    # Assert
    assert "_renderAnnotationLayer" in text
