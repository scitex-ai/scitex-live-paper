"""No-mocks tests for the merged ``api/dashboard`` boot endpoint.

`api/dashboard` is a thin wrapper that calls the existing
`bundle-info` + `claims` handlers and returns their outputs under
`bundle` and `claims` keys. Saves the SPA two round-trips at boot.

Tests check both halves of the merged payload + verify the merged
shape matches the underlying endpoints exactly (so the dashboard
can never drift from the contracts it wraps).

Real Django test Client + real bundle fixtures. No
``monkeypatch``, no ``mock.patch``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator

import pytest

pytest.importorskip("django")

from django.test import Client  # noqa: E402

from scitex_live_paper._django import services  # noqa: E402

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures"
BUNDLE_MIN = FIXTURES / "bundle-min"
BUNDLE_ACCEPTED = FIXTURES / "bundle-accepted"


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


@pytest.fixture
def client() -> Client:
    return Client()


def _pin(path: Path) -> None:
    os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = str(path)
    services.clear_cache()


# ──────────────────────────────────────────────────────────────────
# Endpoint shape
# ──────────────────────────────────────────────────────────────────


def test_api_dashboard_returns_200(client, env_snapshot):
    # Arrange
    # Act
    _pin(BUNDLE_MIN)
    # Assert
    assert client.get("/api/dashboard").status_code == 200


def test_api_dashboard_returns_bundle_key__assert_bundle_in_body(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_MIN)
    # Act
    body = json.loads(client.get("/api/dashboard").content)
    # Assert
    assert "bundle" in body


def test_api_dashboard_returns_bundle_key__assert_isinstance_body_bundle_di(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_MIN)
    # Act
    body = json.loads(client.get("/api/dashboard").content)
    # Assert
    assert isinstance(body["bundle"], dict)




def test_api_dashboard_returns_claims_key__assert_claims_in_body(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_MIN)
    # Act
    body = json.loads(client.get("/api/dashboard").content)
    # Assert
    assert "claims" in body


def test_api_dashboard_returns_claims_key__assert_isinstance_body_claims_di(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_MIN)
    # Act
    body = json.loads(client.get("/api/dashboard").content)
    # Assert
    assert isinstance(body["claims"], dict)




# ──────────────────────────────────────────────────────────────────
# Merged shape matches the underlying endpoints exactly
# ──────────────────────────────────────────────────────────────────


def test_dashboard_bundle_matches_bundle_info_endpoint(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_MIN)
    bundle_info = json.loads(client.get("/api/bundle-info").content)
    # Act
    dashboard = json.loads(client.get("/api/dashboard").content)
    # Assert
    assert dashboard["bundle"] == bundle_info


def test_dashboard_claims_matches_claims_endpoint(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_MIN)
    claims_only = json.loads(client.get("/api/claims").content)
    # Act
    dashboard = json.loads(client.get("/api/dashboard").content)
    # Assert
    assert dashboard["claims"] == claims_only


# ──────────────────────────────────────────────────────────────────
# Carries paper_state + re_verify_enabled + claim count
# ──────────────────────────────────────────────────────────────────


def test_dashboard_carries_paper_state_under_bundle__assert_ps_stage_accepted(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    body = json.loads(client.get("/api/dashboard").content)
    ps = body["bundle"]["paper_state"]
    # Assert
    assert ps["stage"] == "accepted"


def test_dashboard_carries_paper_state_under_bundle__assert_ps_journal_elife(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    body = json.loads(client.get("/api/dashboard").content)
    ps = body["bundle"]["paper_state"]
    # Assert
    assert ps["journal"] == "eLife"


def test_dashboard_carries_paper_state_under_bundle__assert_ps_re_verify_enabled_is_t(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    body = json.loads(client.get("/api/dashboard").content)
    ps = body["bundle"]["paper_state"]
    # Assert
    assert ps["re_verify_enabled"] is True




def test_dashboard_carries_re_verify_enabled_under_claims__assert_body_claims_re_verify_ena(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    body = json.loads(client.get("/api/dashboard").content)
    # Assert
    assert body["claims"]["re_verify_enabled"] is True


def test_dashboard_carries_re_verify_enabled_under_claims__assert_body_claims_pinned_commit(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    body = json.loads(client.get("/api/dashboard").content)
    # Assert
    assert body["claims"]["pinned_commit"] == "deadbeefcafef00d12345678"




def test_dashboard_claim_count_matches_array_length__assert_body_claims_claim_count_3(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_MIN)
    # Act
    body = json.loads(client.get("/api/dashboard").content)
    # Assert
    assert body["claims"]["claim_count"] == 3


def test_dashboard_claim_count_matches_array_length__assert_len_body_claims_claims_3(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_MIN)
    # Act
    body = json.loads(client.get("/api/dashboard").content)
    # Assert
    assert len(body["claims"]["claims"]) == 3




def test_dashboard_includes_re_review_badge_null_when_absent(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    body = json.loads(client.get("/api/dashboard").content)
    # Assert
    assert body["bundle"]["re_review_badge"] is None


# ──────────────────────────────────────────────────────────────────
# BundleContext (M4) badge surfaces via mount(resolver=...)
# ──────────────────────────────────────────────────────────────────


def test_dashboard_surfaces_re_review_badge_via_mount__assert_body_bundle_re_review_bad(env_snapshot):
    # Arrange
    from django.test import RequestFactory
    from scitex_live_paper import (
        BundleContext, BundleSource, ReReviewBadge, mount,
    )
    badge = ReReviewBadge(
        status="verified",
        reviewer="agentic-journal-v3",
    )
    def resolver(request, **kw):
        return BundleContext(
            source=BundleSource.from_directory(BUNDLE_ACCEPTED),
            re_review_badge=badge,
        )
    patterns, _ = mount(resolver)
    dispatch = next(p.callback for p in patterns if p.name == "api_dispatch")
    response = dispatch(
        RequestFactory().get("/api/dashboard"),
        endpoint="api/dashboard",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["bundle"]["re_review_badge"]["status"] == "verified"


def test_dashboard_surfaces_re_review_badge_via_mount__assert_body_bundle_re_review_bad_2(env_snapshot):
    # Arrange
    from django.test import RequestFactory
    from scitex_live_paper import (
        BundleContext, BundleSource, ReReviewBadge, mount,
    )
    badge = ReReviewBadge(
        status="verified",
        reviewer="agentic-journal-v3",
    )
    def resolver(request, **kw):
        return BundleContext(
            source=BundleSource.from_directory(BUNDLE_ACCEPTED),
            re_review_badge=badge,
        )
    patterns, _ = mount(resolver)
    dispatch = next(p.callback for p in patterns if p.name == "api_dispatch")
    response = dispatch(
        RequestFactory().get("/api/dashboard"),
        endpoint="api/dashboard",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["bundle"]["re_review_badge"]["reviewer"] == "agentic-journal-v3"




# ──────────────────────────────────────────────────────────────────
# HANDLERS registration
# ──────────────────────────────────────────────────────────────────


def test_handlers_registry_includes_api_dashboard():
    # Arrange
    from scitex_live_paper._django.handlers import HANDLERS, handle_dashboard
    # Act
    # Assert
    assert HANDLERS["api/dashboard"] is handle_dashboard


# ──────────────────────────────────────────────────────────────────
# Existing endpoints unchanged (regression — additive PR)
# ──────────────────────────────────────────────────────────────────


def test_existing_bundle_info_endpoint_still_reachable(client, env_snapshot):
    # Arrange
    # Act
    _pin(BUNDLE_MIN)
    # Assert
    assert client.get("/api/bundle-info").status_code == 200


def test_existing_claims_endpoint_still_reachable(client, env_snapshot):
    # Arrange
    # Act
    _pin(BUNDLE_MIN)
    # Assert
    assert client.get("/api/claims").status_code == 200


def test_existing_ping_endpoint_still_reachable(client, env_snapshot):
    # Arrange
    # Act
    _pin(BUNDLE_MIN)
    # Assert
    assert client.get("/api/ping").status_code == 200
