"""No-mocks tests for the embed-mode SPA shell variant.

Host apps (``scitex-hub`` project view, ``scitex-writer`` preview,
``scitex-scholar``) iframe the live-paper viewer into their own page
chrome. The viewer responds to ``?embed=1`` with a stripped-down
template (no header, no subtitle, no status pre) that drops cleanly
into a host iframe.

All collaborators are real:
- Django ``RequestFactory`` builds the request — same lever Django's
  own unit tests use, not a mock.
- The actual template loader walks the real app's
  ``templates/live_paper/`` directory.
"""

from __future__ import annotations

import pytest

pytest.importorskip("django")

from django.test import RequestFactory  # noqa: E402

from scitex_live_paper._django import views  # noqa: E402


@pytest.fixture
def rf() -> RequestFactory:
    return RequestFactory()


# ──────────────────────────────────────────────────────────────────
# Default (no query string) — full standalone shell
# ──────────────────────────────────────────────────────────────────


def test_viewer_page_default_returns_full_chrome__assert_response_status_code_200(rf):
    # Arrange
    request = rf.get("/")
    response = views.viewer_page(request)
    # Act
    body = response.content.decode("utf-8")
    # Assert
    assert response.status_code == 200


def test_viewer_page_default_returns_full_chrome__assert_app_header_in_body(rf):
    # Arrange — chrome comes from the canonical SDK AppHeader (stats
    # pattern); the leaf renders no <header> of its own.
    request = rf.get("/")
    response = views.viewer_page(request)
    # Act
    body = response.content.decode("utf-8")
    # Assert
    assert "data-stx-app-header" in body


def test_viewer_page_default_returns_full_chrome__assert_app_title_in_body(rf):
    # Arrange — leaf identity is the AppHeader title, never an h1.
    request = rf.get("/")
    response = views.viewer_page(request)
    # Act
    body = response.content.decode("utf-8")
    # Assert
    assert 'data-app-title="SciTeX Live Paper"' in body




def test_viewer_page_default_omits_embed_data_attribute(rf):
    # Arrange
    # Act
    body = views.viewer_page(rf.get("/")).content.decode("utf-8")
    # Assert
    assert 'data-embed-mode' not in body


def test_viewer_page_default_carries_data_api_base(rf):
    # Arrange
    # Act
    body = views.viewer_page(rf.get("/")).content.decode("utf-8")
    # Assert
    assert 'data-api-base="/api/"' in body


# ──────────────────────────────────────────────────────────────────
# ?embed=1 — minimal chrome-less shell
# ──────────────────────────────────────────────────────────────────


def test_viewer_page_embed_one_returns_200(rf):
    # Arrange
    # Act
    response = views.viewer_page(rf.get("/?embed=1"))
    # Assert
    assert response.status_code == 200


def test_viewer_page_embed_one_strips_header__assert_header_not_in_body(rf):
    # Arrange
    # Act
    body = views.viewer_page(rf.get("/?embed=1")).content.decode("utf-8")
    # Assert
    assert "<header" not in body


def test_viewer_page_embed_one_strips_header__assert_read_only_viewer_for_acce(rf):
    # Arrange
    # Act
    body = views.viewer_page(rf.get("/?embed=1")).content.decode("utf-8")
    # Assert
    assert "Read-only viewer for accepted manuscript bundles." not in body




def test_viewer_page_embed_one_strips_subtitle_text(rf):
    # Arrange
    # Act
    body = views.viewer_page(rf.get("/?embed=1")).content.decode("utf-8")
    # Assert
    assert "Claim model owned upstream" not in body


def test_viewer_page_embed_one_carries_data_api_base(rf):
    # Arrange
    # Act
    body = views.viewer_page(rf.get("/?embed=1")).content.decode("utf-8")
    # Assert
    assert 'data-api-base="/api/"' in body


def test_viewer_page_embed_one_carries_data_embed_mode(rf):
    # Arrange
    # Act
    body = views.viewer_page(rf.get("/?embed=1")).content.decode("utf-8")
    # Assert
    assert 'data-embed-mode="1"' in body


def test_viewer_page_embed_one_carries_root_div(rf):
    # Arrange
    # Act
    body = views.viewer_page(rf.get("/?embed=1")).content.decode("utf-8")
    # Assert
    assert 'id="live-paper-root"' in body


def test_viewer_page_embed_one_links_same_css(rf):
    # Arrange
    # Act
    body = views.viewer_page(rf.get("/?embed=1")).content.decode("utf-8")
    # Assert
    assert "live_paper/css/viewer.css" in body


def test_viewer_page_embed_one_links_same_js(rf):
    # Arrange
    # Act
    body = views.viewer_page(rf.get("/?embed=1")).content.decode("utf-8")
    # Assert
    assert "live_paper/js/viewer.js" in body


def test_viewer_page_embed_one_is_cdn_free(rf):
    # Arrange
    # Act
    body = views.viewer_page(rf.get("/?embed=1")).content.decode("utf-8")
    # Assert
    for marker in ("cdn.jsdelivr.net", "unpkg.com", "cdnjs.cloudflare.com"):
        assert marker not in body


def test_viewer_page_embed_one_adds_embed_body_class(rf):
    # Arrange
    # Act
    body = views.viewer_page(rf.get("/?embed=1")).content.decode("utf-8")
    # Assert
    assert 'class="live-paper-embed"' in body


# ──────────────────────────────────────────────────────────────────
# Embed switch — case-insensitive truthy values, falsy values, absent
# ──────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "value",
    ["1", "true", "True", "TRUE", "yes", "YES", "on", "ON", "  true  "],
)
def test_embed_mode_truthy_values_select_embed_shell(rf, value):
    # arrange
    request = rf.get(f"/?embed={value}")
    # act
    is_embed = views._is_embed_mode(request)
    # assert
    assert is_embed is True


@pytest.mark.parametrize(
    "value",
    ["0", "false", "False", "no", "off", "", "random-string"],
)
def test_embed_mode_falsy_or_unknown_values_keep_full_chrome(rf, value):
    # arrange
    request = rf.get(f"/?embed={value}")
    # act
    is_embed = views._is_embed_mode(request)
    # assert
    assert is_embed is False


def test_embed_mode_absent_param_keeps_full_chrome(rf):
    # Arrange
    # Act
    request = rf.get("/")
    # Assert
    assert views._is_embed_mode(request) is False


def test_embed_mode_other_query_params_dont_trigger__assert_app_header_in_body(rf):
    # Arrange
    # Act
    body = views.viewer_page(rf.get("/?foo=1&bar=true")).content.decode("utf-8")
    # Assert
    assert "data-stx-app-header" in body


def test_embed_mode_other_query_params_dont_trigger__assert_data_embed_mode_not_in_bo(rf):
    # Arrange
    # Act
    body = views.viewer_page(rf.get("/?foo=1&bar=true")).content.decode("utf-8")
    # Assert
    assert 'data-embed-mode' not in body




# ──────────────────────────────────────────────────────────────────
# Default and embed shells stay structurally aligned
# ──────────────────────────────────────────────────────────────────


def test_both_shells_share_live_paper_root_id__assert_id_live_paper_root_in_def(rf):
    # Arrange
    default_body = views.viewer_page(rf.get("/")).content.decode("utf-8")
    # Act
    embed_body = views.viewer_page(rf.get("/?embed=1")).content.decode("utf-8")
    # Assert
    assert 'id="live-paper-root"' in default_body


def test_both_shells_share_live_paper_root_id__assert_id_live_paper_root_in_emb(rf):
    # Arrange
    default_body = views.viewer_page(rf.get("/")).content.decode("utf-8")
    # Act
    embed_body = views.viewer_page(rf.get("/?embed=1")).content.decode("utf-8")
    # Assert
    assert 'id="live-paper-root"' in embed_body




def test_both_shells_share_bundle_info_pre_id__assert_id_live_paper_bundle_info(rf):
    # Arrange
    default_body = views.viewer_page(rf.get("/")).content.decode("utf-8")
    # Act
    embed_body = views.viewer_page(rf.get("/?embed=1")).content.decode("utf-8")
    # Assert
    assert 'id="live-paper-bundle-info"' in default_body


def test_both_shells_share_bundle_info_pre_id__assert_id_live_paper_bundle_info_2(rf):
    # Arrange
    default_body = views.viewer_page(rf.get("/")).content.decode("utf-8")
    # Act
    embed_body = views.viewer_page(rf.get("/?embed=1")).content.decode("utf-8")
    # Assert
    assert 'id="live-paper-bundle-info"' in embed_body


