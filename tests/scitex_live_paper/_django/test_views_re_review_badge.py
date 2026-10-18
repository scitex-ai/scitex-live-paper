"""No-mocks tests for the M4 paper-level re-review badge.

Verifies:
1. `ReReviewBadge` + `ReReviewStatus` are importable from the top-level
   package + are in `__all__`.
2. `BundleContext.re_review_badge` is an optional field (default `None`).
3. `api/bundle-info` surfaces the badge when present, `null` when absent.
4. The badge field flows through `mount(resolver=...)` correctly.
5. SPA JS / CSS source ships the rendering surface.

All collaborators are real — real Django test Client, real fixtures,
real BundleContext objects. No `monkeypatch`, no `mock.patch`.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator, get_args

import pytest

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"
BUNDLE_ACCEPTED = FIXTURES / "bundle-accepted"


# ──────────────────────────────────────────────────────────────────
# Top-level re-export contract
# ──────────────────────────────────────────────────────────────────


def test_re_review_badge_importable_from_top_level__assert_hasattr_lp_rereviewbadge():
    # Arrange
    # Act
    import scitex_live_paper as lp
    # Assert
    assert hasattr(lp, "ReReviewBadge")


def test_re_review_badge_importable_from_top_level__assert_hasattr_lp_rereviewstatus():
    # Arrange
    # Act
    import scitex_live_paper as lp
    # Assert
    assert hasattr(lp, "ReReviewStatus")




def test_re_review_badge_in_all__assert_rereviewbadge_in_lp_all():
    # Arrange
    # Act
    import scitex_live_paper as lp
    # Assert
    assert "ReReviewBadge" in lp.__all__


def test_re_review_badge_in_all__assert_rereviewstatus_in_lp_all():
    # Arrange
    # Act
    import scitex_live_paper as lp
    # Assert
    assert "ReReviewStatus" in lp.__all__




# ──────────────────────────────────────────────────────────────────
# ReReviewStatus + ReReviewBadge dataclass contract
# ──────────────────────────────────────────────────────────────────


def test_re_review_status_literal_lists_four_stages():
    # Arrange
    from scitex_live_paper import ReReviewStatus
    # Act
    stages = set(get_args(ReReviewStatus))
    # Assert
    assert stages == {"verified", "concerns", "contradicted", "stale"}


def test_re_review_badge_status_required():
    # Arrange
    from scitex_live_paper import ReReviewBadge
    # Act
    badge = ReReviewBadge(status="verified")
    # Assert
    assert badge.status == "verified"


def test_re_review_badge_all_other_fields_default_to_none__assert_badge_last_reviewed_at_is():
    # Arrange
    from scitex_live_paper import ReReviewBadge
    # Act
    badge = ReReviewBadge(status="stale")
    # Assert
    assert badge.last_reviewed_at is None


def test_re_review_badge_all_other_fields_default_to_none__assert_badge_reviewer_is_none():
    # Arrange
    from scitex_live_paper import ReReviewBadge
    # Act
    badge = ReReviewBadge(status="stale")
    # Assert
    assert badge.reviewer is None


def test_re_review_badge_all_other_fields_default_to_none__assert_badge_log_url_is_none():
    # Arrange
    from scitex_live_paper import ReReviewBadge
    # Act
    badge = ReReviewBadge(status="stale")
    # Assert
    assert badge.log_url is None


def test_re_review_badge_all_other_fields_default_to_none__assert_badge_notes_is_none():
    # Arrange
    from scitex_live_paper import ReReviewBadge
    # Act
    badge = ReReviewBadge(status="stale")
    # Assert
    assert badge.notes is None




def test_re_review_badge_is_frozen():
    # Arrange
    from scitex_live_paper import ReReviewBadge
    # Act
    badge = ReReviewBadge(status="verified")
    # Assert
    with pytest.raises(Exception):
        badge.status = "stale"  # type: ignore[misc]


def test_re_review_badge_carries_all_fields__assert_badge_status_concerns():
    # Arrange
    from scitex_live_paper import ReReviewBadge
    # Act
    badge = ReReviewBadge(
        status="concerns",
        last_reviewed_at="2026-06-13T03:00:00Z",
        reviewer="agentic-journal-v3",
        log_url="https://journal.scitex.ai/reviews/abc",
        notes="One claim's effect size shrinks under the new control.",
    )
    # Assert
    assert badge.status == "concerns"


def test_re_review_badge_carries_all_fields__assert_badge_reviewer_agentic_jo():
    # Arrange
    from scitex_live_paper import ReReviewBadge
    # Act
    badge = ReReviewBadge(
        status="concerns",
        last_reviewed_at="2026-06-13T03:00:00Z",
        reviewer="agentic-journal-v3",
        log_url="https://journal.scitex.ai/reviews/abc",
        notes="One claim's effect size shrinks under the new control.",
    )
    # Assert
    assert badge.reviewer == "agentic-journal-v3"


def test_re_review_badge_carries_all_fields__assert_scitex_ai_in_badge_log_ur():
    # Arrange
    from scitex_live_paper import ReReviewBadge
    # Act
    badge = ReReviewBadge(
        status="concerns",
        last_reviewed_at="2026-06-13T03:00:00Z",
        reviewer="agentic-journal-v3",
        log_url="https://journal.scitex.ai/reviews/abc",
        notes="One claim's effect size shrinks under the new control.",
    )
    # Assert
    assert "scitex.ai" in badge.log_url




# ──────────────────────────────────────────────────────────────────
# BundleContext.re_review_badge field
# ──────────────────────────────────────────────────────────────────


def test_bundle_context_re_review_badge_defaults_to_none():
    # Arrange
    from scitex_live_paper import BundleContext, BundleSource
    # Act
    ctx = BundleContext(source=BundleSource.from_directory(BUNDLE_ACCEPTED))
    # Assert
    assert ctx.re_review_badge is None


def test_bundle_context_carries_re_review_badge_through__assert_ctx_re_review_badge_is_ba():
    # Arrange
    from scitex_live_paper import BundleContext, BundleSource, ReReviewBadge
    badge = ReReviewBadge(status="verified", reviewer="agentic-journal-v3")
    # Act
    ctx = BundleContext(
        source=BundleSource.from_directory(BUNDLE_ACCEPTED),
        re_review_badge=badge,
    )
    # Assert
    assert ctx.re_review_badge is badge


def test_bundle_context_carries_re_review_badge_through__assert_ctx_re_review_badge_statu():
    # Arrange
    from scitex_live_paper import BundleContext, BundleSource, ReReviewBadge
    badge = ReReviewBadge(status="verified", reviewer="agentic-journal-v3")
    # Act
    ctx = BundleContext(
        source=BundleSource.from_directory(BUNDLE_ACCEPTED),
        re_review_badge=badge,
    )
    # Assert
    assert ctx.re_review_badge.status == "verified"




# ──────────────────────────────────────────────────────────────────
# bundle-info handler surfaces the badge
# ──────────────────────────────────────────────────────────────────


pytest.importorskip("django")


@pytest.fixture
def env_snapshot() -> Iterator[None]:
    snap = dict(os.environ)
    try:
        yield
    finally:
        for k in list(os.environ):
            if k not in snap:
                del os.environ[k]
        for k, v in snap.items():
            os.environ[k] = v


def test_bundle_info_returns_null_re_review_badge_when_absent__assert_re_review_badge_in_body(env_snapshot):
    # Arrange
    from django.test import Client
    from scitex_live_paper._django import services
    os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = str(BUNDLE_ACCEPTED)
    services.clear_cache()
    # Act
    body = json.loads(Client().get("/api/bundle-info").content)
    # Assert
    assert "re_review_badge" in body


def test_bundle_info_returns_null_re_review_badge_when_absent__assert_body_re_review_badge_is_n(env_snapshot):
    # Arrange
    from django.test import Client
    from scitex_live_paper._django import services
    os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = str(BUNDLE_ACCEPTED)
    services.clear_cache()
    # Act
    body = json.loads(Client().get("/api/bundle-info").content)
    # Assert
    assert body["re_review_badge"] is None




def test_bundle_info_surfaces_re_review_badge_via_mount_resolver__assert_body_re_review_badge_is_n_2(env_snapshot):
    # Arrange
    from django.test import RequestFactory
    from scitex_live_paper import (
        BundleContext, BundleSource, ReReviewBadge, mount,
    )
    badge = ReReviewBadge(
        status="verified",
        reviewer="agentic-journal-v3",
        last_reviewed_at="2026-06-13T03:00:00Z",
        log_url="https://journal.scitex.ai/reviews/r-123",
        notes="No issues found in the second pass.",
    )
    def resolver(request, **kw):
        return BundleContext(
            source=BundleSource.from_directory(BUNDLE_ACCEPTED),
            re_review_badge=badge,
        )
    patterns, _ = mount(resolver)
    dispatch = next(p.callback for p in patterns if p.name == "api_dispatch")
    response = dispatch(
        RequestFactory().get("/api/bundle-info"),
        endpoint="api/bundle-info",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["re_review_badge"] is not None


def test_bundle_info_surfaces_re_review_badge_via_mount_resolver__assert_surfaced_status_verified(env_snapshot):
    # Arrange
    from django.test import RequestFactory
    from scitex_live_paper import (
        BundleContext, BundleSource, ReReviewBadge, mount,
    )
    badge = ReReviewBadge(
        status="verified",
        reviewer="agentic-journal-v3",
        last_reviewed_at="2026-06-13T03:00:00Z",
        log_url="https://journal.scitex.ai/reviews/r-123",
        notes="No issues found in the second pass.",
    )
    def resolver(request, **kw):
        return BundleContext(
            source=BundleSource.from_directory(BUNDLE_ACCEPTED),
            re_review_badge=badge,
        )
    patterns, _ = mount(resolver)
    dispatch = next(p.callback for p in patterns if p.name == "api_dispatch")
    response = dispatch(
        RequestFactory().get("/api/bundle-info"),
        endpoint="api/bundle-info",
    )
    # Act
    body = json.loads(response.content)
    surfaced = body["re_review_badge"]
    # Assert
    assert surfaced["status"] == "verified"


def test_bundle_info_surfaces_re_review_badge_via_mount_resolver__assert_surfaced_reviewer_agentic(env_snapshot):
    # Arrange
    from django.test import RequestFactory
    from scitex_live_paper import (
        BundleContext, BundleSource, ReReviewBadge, mount,
    )
    badge = ReReviewBadge(
        status="verified",
        reviewer="agentic-journal-v3",
        last_reviewed_at="2026-06-13T03:00:00Z",
        log_url="https://journal.scitex.ai/reviews/r-123",
        notes="No issues found in the second pass.",
    )
    def resolver(request, **kw):
        return BundleContext(
            source=BundleSource.from_directory(BUNDLE_ACCEPTED),
            re_review_badge=badge,
        )
    patterns, _ = mount(resolver)
    dispatch = next(p.callback for p in patterns if p.name == "api_dispatch")
    response = dispatch(
        RequestFactory().get("/api/bundle-info"),
        endpoint="api/bundle-info",
    )
    # Act
    body = json.loads(response.content)
    surfaced = body["re_review_badge"]
    # Assert
    assert surfaced["reviewer"] == "agentic-journal-v3"


def test_bundle_info_surfaces_re_review_badge_via_mount_resolver__assert_surfaced_last_reviewed_at(env_snapshot):
    # Arrange
    from django.test import RequestFactory
    from scitex_live_paper import (
        BundleContext, BundleSource, ReReviewBadge, mount,
    )
    badge = ReReviewBadge(
        status="verified",
        reviewer="agentic-journal-v3",
        last_reviewed_at="2026-06-13T03:00:00Z",
        log_url="https://journal.scitex.ai/reviews/r-123",
        notes="No issues found in the second pass.",
    )
    def resolver(request, **kw):
        return BundleContext(
            source=BundleSource.from_directory(BUNDLE_ACCEPTED),
            re_review_badge=badge,
        )
    patterns, _ = mount(resolver)
    dispatch = next(p.callback for p in patterns if p.name == "api_dispatch")
    response = dispatch(
        RequestFactory().get("/api/bundle-info"),
        endpoint="api/bundle-info",
    )
    # Act
    body = json.loads(response.content)
    surfaced = body["re_review_badge"]
    # Assert
    assert surfaced["last_reviewed_at"] == "2026-06-13T03:00:00Z"


def test_bundle_info_surfaces_re_review_badge_via_mount_resolver__assert_surfaced_log_url_startswi(env_snapshot):
    # Arrange
    from django.test import RequestFactory
    from scitex_live_paper import (
        BundleContext, BundleSource, ReReviewBadge, mount,
    )
    badge = ReReviewBadge(
        status="verified",
        reviewer="agentic-journal-v3",
        last_reviewed_at="2026-06-13T03:00:00Z",
        log_url="https://journal.scitex.ai/reviews/r-123",
        notes="No issues found in the second pass.",
    )
    def resolver(request, **kw):
        return BundleContext(
            source=BundleSource.from_directory(BUNDLE_ACCEPTED),
            re_review_badge=badge,
        )
    patterns, _ = mount(resolver)
    dispatch = next(p.callback for p in patterns if p.name == "api_dispatch")
    response = dispatch(
        RequestFactory().get("/api/bundle-info"),
        endpoint="api/bundle-info",
    )
    # Act
    body = json.loads(response.content)
    surfaced = body["re_review_badge"]
    # Assert
    assert surfaced["log_url"].startswith("https://journal.scitex.ai")


def test_bundle_info_surfaces_re_review_badge_via_mount_resolver__assert_surfaced_notes(env_snapshot):
    # Arrange
    from django.test import RequestFactory
    from scitex_live_paper import (
        BundleContext, BundleSource, ReReviewBadge, mount,
    )
    badge = ReReviewBadge(
        status="verified",
        reviewer="agentic-journal-v3",
        last_reviewed_at="2026-06-13T03:00:00Z",
        log_url="https://journal.scitex.ai/reviews/r-123",
        notes="No issues found in the second pass.",
    )
    def resolver(request, **kw):
        return BundleContext(
            source=BundleSource.from_directory(BUNDLE_ACCEPTED),
            re_review_badge=badge,
        )
    patterns, _ = mount(resolver)
    dispatch = next(p.callback for p in patterns if p.name == "api_dispatch")
    response = dispatch(
        RequestFactory().get("/api/bundle-info"),
        endpoint="api/bundle-info",
    )
    # Act
    body = json.loads(response.content)
    surfaced = body["re_review_badge"]
    # Assert
    assert surfaced["notes"]




@pytest.mark.parametrize(
    "status",
    ["verified", "concerns", "contradicted", "stale"],
)
def test_bundle_info_each_status_flows_through(env_snapshot, status):
    # arrange
    from django.test import RequestFactory
    from scitex_live_paper import (
        BundleContext, BundleSource, ReReviewBadge, mount,
    )

    def resolver(request, **kw):
        return BundleContext(
            source=BundleSource.from_directory(BUNDLE_ACCEPTED),
            re_review_badge=ReReviewBadge(status=status),
        )

    patterns, _ = mount(resolver)
    dispatch = next(p.callback for p in patterns if p.name == "api_dispatch")
    # act
    response = dispatch(
        RequestFactory().get("/api/bundle-info"),
        endpoint="api/bundle-info",
    )
    # assert
    body = json.loads(response.content)
    assert body["re_review_badge"]["status"] == status


# ──────────────────────────────────────────────────────────────────
# SPA UI source — JS module + CSS palette
# ──────────────────────────────────────────────────────────────────


def _js_module(name: str) -> str:
    import scitex_live_paper

    pkg_root = Path(scitex_live_paper.__file__).resolve().parent
    return (pkg_root / "_django/static/live_paper/js" / name).read_text(encoding="utf-8")


def _viewer_css() -> str:
    import scitex_live_paper

    pkg_root = Path(scitex_live_paper.__file__).resolve().parent
    return (pkg_root / "_django/static/live_paper/css/viewer.css").read_text(encoding="utf-8")


def test_re_review_badge_js_module_exists_and_exports():
    # Arrange
    # Act
    text = _js_module("re-review-badge.js")
    # Assert
    assert "export function renderReReviewBadge" in text


def test_viewer_js_orchestrator_imports_re_review_badge__assert_from_re_review_badge_js_i():
    # Arrange
    # Act
    text = _js_module("viewer.js")
    # Assert
    assert 'from "./re-review-badge.js"' in text


def test_viewer_js_orchestrator_imports_re_review_badge__assert_renderrereviewbadge_roote():
    # Arrange
    # Act
    text = _js_module("viewer.js")
    # Assert
    assert "renderReReviewBadge(rootEl, " in text




def test_re_review_badge_js_reads_payload_field__assert_re_review_badge_in_text():
    # Arrange
    # Act
    text = _js_module("re-review-badge.js")
    # Assert
    assert "re_review_badge" in text


def test_re_review_badge_js_reads_payload_field__assert_badge_status_in_text():
    # Arrange
    # Act
    text = _js_module("re-review-badge.js")
    # Assert
    assert "badge.status" in text




def test_re_review_badge_js_renders_optional_fields():
    # Arrange
    # Act
    text = _js_module("re-review-badge.js")
    # Assert
    for needle in ("reviewer", "last_reviewed_at", "notes", "log_url"):
        assert needle in text, f"missing field render: {needle}"


def test_re_review_badge_js_target_blank_on_log_link():
    # Arrange
    # Act
    text = _js_module("re-review-badge.js")
    # Assert
    assert 'target = "_blank"' in text or 'target="_blank"' in text


def test_viewer_css_re_review_badge_base_class():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert ".lp-re-review-badge" in text


def test_viewer_css_styles_re_review_badge():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert — one assertion per loop iteration: per-status border-left
    # mirrors the M2 chip palette
    for status in ("verified", "stale", "contradicted", "concerns"):
        assert f'data-status="{status}"' in text


def test_viewer_css_styles_re_review_badge_label_and_log_link__assert_lp_re_review_badge_label():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert ".lp-re-review-badge-label" in text


def test_viewer_css_styles_re_review_badge_label_and_log_link__assert_lp_re_review_badge_log_in():
    # Arrange
    # Act
    text = _viewer_css()
    # Assert
    assert ".lp-re-review-badge-log" in text


