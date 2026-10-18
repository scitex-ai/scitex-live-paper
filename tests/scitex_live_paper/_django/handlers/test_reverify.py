"""No-mocks tests for M2 re-verify endpoint.

Three classes of test:

1. **Method + body validation** — POST-only, JSON body, required claim_id,
   pinned_commit fallback chain.
2. **Graceful degradation** — when ``scitex-clew`` is not installed
   (the realistic case for fresh installs without the upstream package)
   the handler returns a labelled fallback response, never a 500.
3. **clew-installed integration** — when scitex-clew IS importable
   (real module-state via ``sys.modules`` injection — same lever PR (a)
   used for the no-django ImportError branch), the handler calls the
   real ``verify_claim`` and shapes its return into our envelope.

All collaborators are real. No ``monkeypatch``, no ``mock.patch``.
Real Django test ``Client`` + real bundle fixtures + real
``sys.modules`` manipulation in yield-fixtures with full restore.
"""

from __future__ import annotations

import json
import os
import sys
import types
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


@pytest.fixture
def no_scitex_clew() -> Iterator[None]:
    """Ensure ``import scitex_clew`` raises ImportError for this test.

    Real ``sys.modules`` state manipulation (not ``mock.patch``):
    write ``None`` to the entry so the next import raises, restore on
    teardown. Same lever PR (a) used for the no-django CLI branch —
    pre-approved by the lead.
    """
    key = "scitex_clew"
    sentinel = object()
    original = sys.modules.get(key, sentinel)
    sys.modules[key] = None  # type: ignore[assignment]
    try:
        yield
    finally:
        if original is sentinel:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = original  # type: ignore[assignment]


@pytest.fixture
def fake_scitex_clew() -> Iterator[types.ModuleType]:
    """Install a real Python module under ``sys.modules["scitex_clew"]``.

    The module exposes a real ``verify_claim`` function the handler
    will call. Tests can configure its behaviour by setting attributes
    on the yielded module (no `mock.patch.object` — direct attribute
    assignment on a real module). Restored on teardown.
    """
    key = "scitex_clew"
    sentinel = object()
    original = sys.modules.get(key, sentinel)
    module = types.ModuleType(key)
    # Default behaviour: return a real-shaped verified result (nested
    # "claim" key + top-level source_verified/chain_verified/details).
    # Tests override.
    module.verify_claim = lambda claim_id_or_location: {
        "claim": {
            "claim_id": claim_id_or_location,
            "status": "verified",
            "verified_at": "2026-06-13T00:00:00Z",
        },
        "source_verified": True,
        "chain_verified": True,
        "details": ["Source file hash matches", "Chain verified (1 runs)"],
    }
    sys.modules[key] = module
    try:
        yield module
    finally:
        if original is sentinel:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = original  # type: ignore[assignment]


# ──────────────────────────────────────────────────────────────────
# Method + body validation
# ──────────────────────────────────────────────────────────────────


def test_reverify_get_returns_405__assert_response_status_code_405(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.get("/api/claim/verify")
    # Assert
    assert response.status_code == 405


def test_reverify_get_returns_405__assert_method_not_allowed_in_bod(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.get("/api/claim/verify")
    # Act
    body = json.loads(response.content)
    # Assert
    assert "method not allowed" in body["error"].lower()




def test_reverify_put_returns_405(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.put("/api/claim/verify")
    # Assert
    assert response.status_code == 405


def test_reverify_empty_body_returns_400(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.post("/api/claim/verify", data="", content_type="application/json")
    # Assert
    assert response.status_code == 400


def test_reverify_malformed_json_returns_400(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.post("/api/claim/verify", data="not-json{{", content_type="application/json")
    # Assert
    assert response.status_code == 400


def test_reverify_non_object_body_returns_400__assert_response_status_code_400(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.post(
        "/api/claim/verify",
        data=json.dumps(["claim_a"]),
        content_type="application/json",
    )
    # Assert
    assert response.status_code == 400


def test_reverify_non_object_body_returns_400__assert_json_object_in_body_error(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps(["claim_a"]),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert "JSON object" in body["error"]




def test_reverify_missing_claim_id_returns_400__assert_response_status_code_400_2(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"pinned_commit": "abc"}),
        content_type="application/json",
    )
    # Assert
    assert response.status_code == 400


def test_reverify_missing_claim_id_returns_400__assert_claim_id_in_body_error(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"pinned_commit": "abc"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert "claim_id" in body["error"]




def test_reverify_empty_claim_id_returns_400(client, env_snapshot):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "   "}),
        content_type="application/json",
    )
    # Assert
    assert response.status_code == 400


# ──────────────────────────────────────────────────────────────────
# pinned_commit fallback chain
# ──────────────────────────────────────────────────────────────────


def test_reverify_no_pinned_commit_anywhere_returns_400__assert_response_status_code_400_3(client, env_snapshot, no_scitex_clew):
    # also doesn't supply one. Handler must 400 with a clear message.
    # Arrange
    _pin(BUNDLE_MIN)
    # Act
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Assert
    assert response.status_code == 400


def test_reverify_no_pinned_commit_anywhere_returns_400__assert_pinned_commit_in_body_err(client, env_snapshot, no_scitex_clew):
    # also doesn't supply one. Handler must 400 with a clear message.
    # Arrange
    _pin(BUNDLE_MIN)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert "pinned_commit" in body["error"]




def test_reverify_body_pinned_commit_wins_over_bundle__assert_response_status_code_200(client, env_snapshot, fake_scitex_clew):
    # passes a different one. pinned_commit is METADATA only (clew is
    # git-agnostic and never receives it), so we assert on the
    # response's verified_against echo, and that the fake was called
    # with just the claim_id positionally.
    # Arrange
    captured: dict = {}
    def recorder(claim_id_or_location):
        captured["arg"] = claim_id_or_location
        return {"claim": {"status": "verified"}}
    fake_scitex_clew.verify_claim = recorder
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({
            "claim_id": "claim_a1b2c3d4e5f6",
            "pinned_commit": "body-supplied-commit",
        }),
        content_type="application/json",
    )
    # Assert
    assert response.status_code == 200


def test_reverify_body_pinned_commit_wins_over_bundle__assert_body_verified_against_bod(client, env_snapshot, fake_scitex_clew):
    # passes a different one. pinned_commit is METADATA only (clew is
    # git-agnostic and never receives it), so we assert on the
    # response's verified_against echo, and that the fake was called
    # with just the claim_id positionally.
    # Arrange
    captured: dict = {}
    def recorder(claim_id_or_location):
        captured["arg"] = claim_id_or_location
        return {"claim": {"status": "verified"}}
    fake_scitex_clew.verify_claim = recorder
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({
            "claim_id": "claim_a1b2c3d4e5f6",
            "pinned_commit": "body-supplied-commit",
        }),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["verified_against"] == "body-supplied-commit"


def test_reverify_body_pinned_commit_wins_over_bundle__assert_captured_arg_claim_a1b2c3(client, env_snapshot, fake_scitex_clew):
    # passes a different one. pinned_commit is METADATA only (clew is
    # git-agnostic and never receives it), so we assert on the
    # response's verified_against echo, and that the fake was called
    # with just the claim_id positionally.
    # Arrange
    captured: dict = {}
    def recorder(claim_id_or_location):
        captured["arg"] = claim_id_or_location
        return {"claim": {"status": "verified"}}
    fake_scitex_clew.verify_claim = recorder
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({
            "claim_id": "claim_a1b2c3d4e5f6",
            "pinned_commit": "body-supplied-commit",
        }),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert captured["arg"] == "claim_a1b2c3d4e5f6"




def test_reverify_falls_back_to_bundle_paper_state_commit__assert_body_verified_against_dea(client, env_snapshot, fake_scitex_clew):
    # bundle.paper_state.pinned_commit and echo it as metadata.
    # Arrange
    captured: dict = {}
    def recorder(claim_id_or_location):
        captured["arg"] = claim_id_or_location
        return {"claim": {"status": "verified"}}
    fake_scitex_clew.verify_claim = recorder
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["verified_against"] == "deadbeefcafef00d12345678"


def test_reverify_falls_back_to_bundle_paper_state_commit__assert_captured_arg_claim_a1b2c3_2(client, env_snapshot, fake_scitex_clew):
    # bundle.paper_state.pinned_commit and echo it as metadata.
    # Arrange
    captured: dict = {}
    def recorder(claim_id_or_location):
        captured["arg"] = claim_id_or_location
        return {"claim": {"status": "verified"}}
    fake_scitex_clew.verify_claim = recorder
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert captured["arg"] == "claim_a1b2c3d4e5f6"




# ──────────────────────────────────────────────────────────────────
# Graceful degradation when scitex-clew not installed
# ──────────────────────────────────────────────────────────────────


def test_reverify_without_clew_returns_200_with_fallback_envelope__assert_response_status_code_200_2(client, env_snapshot, no_scitex_clew):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Assert
    assert response.status_code == 200


def test_reverify_without_clew_returns_200_with_fallback_envelope__assert_body_ok_is_false(client, env_snapshot, no_scitex_clew):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["ok"] is False


def test_reverify_without_clew_returns_200_with_fallback_envelope__assert_body_status_stale(client, env_snapshot, no_scitex_clew):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["status"] == "stale"


def test_reverify_without_clew_returns_200_with_fallback_envelope__assert_body_fallback_is_true(client, env_snapshot, no_scitex_clew):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["fallback"] is True


def test_reverify_without_clew_returns_200_with_fallback_envelope__assert_scitex_clew_not_installed(client, env_snapshot, no_scitex_clew):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert "scitex-clew not installed" in body["reason"]




def test_reverify_without_clew_carries_claim_id_back(client, env_snapshot, no_scitex_clew):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["claim_id"] == "claim_a1b2c3d4e5f6"


def _post_verify_partial_clew(client):
    """POST /api/claim/verify with a skew clew (no verify_claim).

    Shared Arrange+Act for the partial-clew tests (each test keeps a
    single assert per STX-TQ007).
    """
    key = "scitex_clew"
    sentinel = object()
    original = sys.modules.get(key, sentinel)
    partial = types.ModuleType(key)
    # NO verify_claim attribute on this module.
    sys.modules[key] = partial
    try:
        _pin(BUNDLE_ACCEPTED)
        response = client.post(
            "/api/claim/verify",
            data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
            content_type="application/json",
        )
        return response, json.loads(response.content)
    finally:
        if original is sentinel:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = original  # type: ignore[assignment]


def test_reverify_with_partial_clew_status_200(client, env_snapshot):
    # Arrange: install a clew module that lacks verify_claim() (e.g.
    # version skew). Handler should degrade gracefully, not 500.
    # Act
    response, _body = _post_verify_partial_clew(client)
    # Assert
    assert response.status_code == 200


def test_reverify_with_partial_clew_falls_back(client, env_snapshot):
    # Arrange
    # Act
    _response, body = _post_verify_partial_clew(client)
    # Assert
    assert body["fallback"] is True


def test_reverify_with_partial_clew_missing_verify_claim_falls_back(client, env_snapshot):
    # Arrange
    # Act
    _response, body = _post_verify_partial_clew(client)
    # Assert
    assert "version skew" in body["reason"]


# ──────────────────────────────────────────────────────────────────
# Happy path — clew installed, real call, envelope shaping
# ──────────────────────────────────────────────────────────────────


def test_reverify_happy_path_returns_200(client, env_snapshot, fake_scitex_clew):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Assert
    assert response.status_code == 200


def test_reverify_happy_path_envelope_ok_true__assert_body_ok_is_true(client, env_snapshot, fake_scitex_clew):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["ok"] is True


def test_reverify_happy_path_envelope_ok_true__assert_body_claim_id_claim_a1b2c(client, env_snapshot, fake_scitex_clew):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["claim_id"] == "claim_a1b2c3d4e5f6"


def test_reverify_happy_path_envelope_ok_true__assert_body_verified_against_dea_2(client, env_snapshot, fake_scitex_clew):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["verified_against"] == "deadbeefcafef00d12345678"


def test_reverify_happy_path_envelope_ok_true__assert_body_status_verified(client, env_snapshot, fake_scitex_clew):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["status"] == "verified"


def test_reverify_happy_path_envelope_ok_true__assert_body_verified_at_2026_06(client, env_snapshot, fake_scitex_clew):
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["verified_at"] == "2026-06-13T00:00:00Z"




def test_reverify_details_aggregates_source_and_chain_verified__assert_details_source_verified_i(client, env_snapshot, fake_scitex_clew):
    # The default fake returns the real shape: top-level source_verified /
    # chain_verified / details list all land in our `details` dict.
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    details = body["details"]
    # Assert
    assert details["source_verified"] is True


def test_reverify_details_aggregates_source_and_chain_verified__assert_details_chain_verified_is(client, env_snapshot, fake_scitex_clew):
    # The default fake returns the real shape: top-level source_verified /
    # chain_verified / details list all land in our `details` dict.
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    details = body["details"]
    # Assert
    assert details["chain_verified"] is True


def test_reverify_details_aggregates_source_and_chain_verified__assert_details_details_source_fi(client, env_snapshot, fake_scitex_clew):
    # The default fake returns the real shape: top-level source_verified /
    # chain_verified / details list all land in our `details` dict.
    # Arrange
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    details = body["details"]
    # Assert
    assert details["details"] == [
        "Source file hash matches",
        "Chain verified (1 runs)",
    ]




@pytest.mark.parametrize("status", ["verified", "suspect", "mismatch", "missing"])
def test_reverify_extracts_nested_claim_status__assert_body_ok_is_true_2(client, env_snapshot, fake_scitex_clew, status):
    # status lives at result["claim"]["status"], NOT top-level.
    # Vocabulary per clew palette v1.3 (clew 0.7.0).
    # Arrange
    def recorder(claim_id_or_location):
        return {
            "claim": {
                "claim_id": claim_id_or_location,
                "status": status,
                "verified_at": "2026-06-13T00:00:00Z" if status == "verified" else None,
            },
            "source_verified": status in {"verified", "suspect"},
            "chain_verified": status == "verified",
            "details": [f"status is {status}"],
        }
    fake_scitex_clew.verify_claim = recorder
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["ok"] is True


@pytest.mark.parametrize("status", ["verified", "suspect", "mismatch", "missing"])
def test_reverify_extracts_nested_claim_status__assert_body_status_status(client, env_snapshot, fake_scitex_clew, status):
    # status lives at result["claim"]["status"], NOT top-level.
    # Vocabulary per clew palette v1.3 (clew 0.7.0).
    # Arrange
    def recorder(claim_id_or_location):
        return {
            "claim": {
                "claim_id": claim_id_or_location,
                "status": status,
                "verified_at": "2026-06-13T00:00:00Z" if status == "verified" else None,
            },
            "source_verified": status in {"verified", "suspect"},
            "chain_verified": status == "verified",
            "details": [f"status is {status}"],
        }
    fake_scitex_clew.verify_claim = recorder
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["status"] == status




def test_reverify_normalizes_legacy_partial_to_suspect__assert_body_ok_is_true_3(client, env_snapshot, fake_scitex_clew):
    # clew 0.7.0 renamed "partial" → "suspect" (same semantic state). A
    # host running an older clew still emits "partial"; the handler must
    # surface it as "suspect" so the SPA palette only sees the v1.3
    # vocabulary (mirrors clew's own read-time normalization).
    # Arrange
    def recorder(claim_id_or_location):
        return {
            "claim": {"claim_id": claim_id_or_location, "status": "partial"},
            "source_verified": True,
            "chain_verified": False,
            "details": ["source ok, chain unverified"],
        }
    fake_scitex_clew.verify_claim = recorder
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["ok"] is True


def test_reverify_normalizes_legacy_partial_to_suspect__assert_body_status_suspect(client, env_snapshot, fake_scitex_clew):
    # clew 0.7.0 renamed "partial" → "suspect" (same semantic state). A
    # host running an older clew still emits "partial"; the handler must
    # surface it as "suspect" so the SPA palette only sees the v1.3
    # vocabulary (mirrors clew's own read-time normalization).
    # Arrange
    def recorder(claim_id_or_location):
        return {
            "claim": {"claim_id": claim_id_or_location, "status": "partial"},
            "source_verified": True,
            "chain_verified": False,
            "details": ["source ok, chain unverified"],
        }
    fake_scitex_clew.verify_claim = recorder
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["status"] == "suspect"




def test_reverify_not_found_result_is_ok_false__assert_response_status_code_200_3(client, env_snapshot, fake_scitex_clew):
    # clew's not-found shape is flat: {"status": "not_found", "message": ...}
    # with NO "claim" key. Handler maps it to ok=False, status="not_found".
    # Arrange
    def recorder(claim_id_or_location):
        return {
            "status": "not_found",
            "message": f"No claim found for '{claim_id_or_location}'",
        }
    fake_scitex_clew.verify_claim = recorder
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_missing"}),
        content_type="application/json",
    )
    # Assert
    assert response.status_code == 200


def test_reverify_not_found_result_is_ok_false__assert_body_ok_is_false_2(client, env_snapshot, fake_scitex_clew):
    # clew's not-found shape is flat: {"status": "not_found", "message": ...}
    # with NO "claim" key. Handler maps it to ok=False, status="not_found".
    # Arrange
    def recorder(claim_id_or_location):
        return {
            "status": "not_found",
            "message": f"No claim found for '{claim_id_or_location}'",
        }
    fake_scitex_clew.verify_claim = recorder
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_missing"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["ok"] is False


def test_reverify_not_found_result_is_ok_false__assert_body_status_not_found(client, env_snapshot, fake_scitex_clew):
    # clew's not-found shape is flat: {"status": "not_found", "message": ...}
    # with NO "claim" key. Handler maps it to ok=False, status="not_found".
    # Arrange
    def recorder(claim_id_or_location):
        return {
            "status": "not_found",
            "message": f"No claim found for '{claim_id_or_location}'",
        }
    fake_scitex_clew.verify_claim = recorder
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_missing"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["status"] == "not_found"


def test_reverify_not_found_result_is_ok_false__assert_body_verified_at_is_none(client, env_snapshot, fake_scitex_clew):
    # clew's not-found shape is flat: {"status": "not_found", "message": ...}
    # with NO "claim" key. Handler maps it to ok=False, status="not_found".
    # Arrange
    def recorder(claim_id_or_location):
        return {
            "status": "not_found",
            "message": f"No claim found for '{claim_id_or_location}'",
        }
    fake_scitex_clew.verify_claim = recorder
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_missing"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["verified_at"] is None


def test_reverify_not_found_result_is_ok_false__assert_no_claim_found_in_body_de(client, env_snapshot, fake_scitex_clew):
    # clew's not-found shape is flat: {"status": "not_found", "message": ...}
    # with NO "claim" key. Handler maps it to ok=False, status="not_found".
    # Arrange
    def recorder(claim_id_or_location):
        return {
            "status": "not_found",
            "message": f"No claim found for '{claim_id_or_location}'",
        }
    fake_scitex_clew.verify_claim = recorder
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_missing"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert "No claim found" in body["details"]




def test_reverify_extra_claim_keys_flow_through_details__assert_status_not_in_details(client, env_snapshot, fake_scitex_clew):
    # bundles them into `details` (forward-compatibility — adding fields
    # upstream doesn't silently change our top-level shape) while still
    # dropping the promoted status/verified_at.
    # Arrange
    fake_scitex_clew.verify_claim = lambda claim_id_or_location: {
        "claim": {
            "claim_id": claim_id_or_location,
            "status": "verified",
            "verified_at": "2026-06-13T00:00:00Z",
            "source_file": "r.csv",
            "extra_future_field": "x",
        },
        "source_verified": True,
        "chain_verified": True,
        "details": ["ok"],
        "new_top_level_key": "y",
    }
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    details = body["details"]
    # Assert
    assert "status" not in details


def test_reverify_extra_claim_keys_flow_through_details__assert_verified_at_not_in_detail(client, env_snapshot, fake_scitex_clew):
    # bundles them into `details` (forward-compatibility — adding fields
    # upstream doesn't silently change our top-level shape) while still
    # dropping the promoted status/verified_at.
    # Arrange
    fake_scitex_clew.verify_claim = lambda claim_id_or_location: {
        "claim": {
            "claim_id": claim_id_or_location,
            "status": "verified",
            "verified_at": "2026-06-13T00:00:00Z",
            "source_file": "r.csv",
            "extra_future_field": "x",
        },
        "source_verified": True,
        "chain_verified": True,
        "details": ["ok"],
        "new_top_level_key": "y",
    }
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    details = body["details"]
    # Assert
    assert "verified_at" not in details


def test_reverify_extra_claim_keys_flow_through_details__assert_details_source_verified_i_2(client, env_snapshot, fake_scitex_clew):
    # bundles them into `details` (forward-compatibility — adding fields
    # upstream doesn't silently change our top-level shape) while still
    # dropping the promoted status/verified_at.
    # Arrange
    fake_scitex_clew.verify_claim = lambda claim_id_or_location: {
        "claim": {
            "claim_id": claim_id_or_location,
            "status": "verified",
            "verified_at": "2026-06-13T00:00:00Z",
            "source_file": "r.csv",
            "extra_future_field": "x",
        },
        "source_verified": True,
        "chain_verified": True,
        "details": ["ok"],
        "new_top_level_key": "y",
    }
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    details = body["details"]
    # Assert
    assert details["source_verified"] is True


def test_reverify_extra_claim_keys_flow_through_details__assert_details_chain_verified_is_2(client, env_snapshot, fake_scitex_clew):
    # bundles them into `details` (forward-compatibility — adding fields
    # upstream doesn't silently change our top-level shape) while still
    # dropping the promoted status/verified_at.
    # Arrange
    fake_scitex_clew.verify_claim = lambda claim_id_or_location: {
        "claim": {
            "claim_id": claim_id_or_location,
            "status": "verified",
            "verified_at": "2026-06-13T00:00:00Z",
            "source_file": "r.csv",
            "extra_future_field": "x",
        },
        "source_verified": True,
        "chain_verified": True,
        "details": ["ok"],
        "new_top_level_key": "y",
    }
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    details = body["details"]
    # Assert
    assert details["chain_verified"] is True


def test_reverify_extra_claim_keys_flow_through_details__assert_details_details_ok(client, env_snapshot, fake_scitex_clew):
    # bundles them into `details` (forward-compatibility — adding fields
    # upstream doesn't silently change our top-level shape) while still
    # dropping the promoted status/verified_at.
    # Arrange
    fake_scitex_clew.verify_claim = lambda claim_id_or_location: {
        "claim": {
            "claim_id": claim_id_or_location,
            "status": "verified",
            "verified_at": "2026-06-13T00:00:00Z",
            "source_file": "r.csv",
            "extra_future_field": "x",
        },
        "source_verified": True,
        "chain_verified": True,
        "details": ["ok"],
        "new_top_level_key": "y",
    }
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    details = body["details"]
    # Assert
    assert details["details"] == ["ok"]


def test_reverify_extra_claim_keys_flow_through_details__assert_details_new_top_level_key(client, env_snapshot, fake_scitex_clew):
    # bundles them into `details` (forward-compatibility — adding fields
    # upstream doesn't silently change our top-level shape) while still
    # dropping the promoted status/verified_at.
    # Arrange
    fake_scitex_clew.verify_claim = lambda claim_id_or_location: {
        "claim": {
            "claim_id": claim_id_or_location,
            "status": "verified",
            "verified_at": "2026-06-13T00:00:00Z",
            "source_file": "r.csv",
            "extra_future_field": "x",
        },
        "source_verified": True,
        "chain_verified": True,
        "details": ["ok"],
        "new_top_level_key": "y",
    }
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    details = body["details"]
    # Assert
    assert details["new_top_level_key"] == "y"


def test_reverify_extra_claim_keys_flow_through_details__assert_details_source_file_r_csv(client, env_snapshot, fake_scitex_clew):
    # bundles them into `details` (forward-compatibility — adding fields
    # upstream doesn't silently change our top-level shape) while still
    # dropping the promoted status/verified_at.
    # Arrange
    fake_scitex_clew.verify_claim = lambda claim_id_or_location: {
        "claim": {
            "claim_id": claim_id_or_location,
            "status": "verified",
            "verified_at": "2026-06-13T00:00:00Z",
            "source_file": "r.csv",
            "extra_future_field": "x",
        },
        "source_verified": True,
        "chain_verified": True,
        "details": ["ok"],
        "new_top_level_key": "y",
    }
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    details = body["details"]
    # Assert
    assert details["source_file"] == "r.csv"


def test_reverify_extra_claim_keys_flow_through_details__assert_details_extra_future_fiel(client, env_snapshot, fake_scitex_clew):
    # bundles them into `details` (forward-compatibility — adding fields
    # upstream doesn't silently change our top-level shape) while still
    # dropping the promoted status/verified_at.
    # Arrange
    fake_scitex_clew.verify_claim = lambda claim_id_or_location: {
        "claim": {
            "claim_id": claim_id_or_location,
            "status": "verified",
            "verified_at": "2026-06-13T00:00:00Z",
            "source_file": "r.csv",
            "extra_future_field": "x",
        },
        "source_verified": True,
        "chain_verified": True,
        "details": ["ok"],
        "new_top_level_key": "y",
    }
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    details = body["details"]
    # Assert
    assert details["extra_future_field"] == "x"




def test_reverify_non_dict_clew_return_stringified__assert_body_ok_is_true_4(client, env_snapshot, fake_scitex_clew):
    # Arrange
    fake_scitex_clew.verify_claim = lambda claim_id_or_location: "verified"
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["ok"] is True


def test_reverify_non_dict_clew_return_stringified__assert_body_status_verified_2(client, env_snapshot, fake_scitex_clew):
    # Arrange
    fake_scitex_clew.verify_claim = lambda claim_id_or_location: "verified"
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["status"] == "verified"


def test_reverify_non_dict_clew_return_stringified__assert_body_verified_at_is_none_2(client, env_snapshot, fake_scitex_clew):
    # Arrange
    fake_scitex_clew.verify_claim = lambda claim_id_or_location: "verified"
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["verified_at"] is None


def test_reverify_non_dict_clew_return_stringified__assert_body_details(client, env_snapshot, fake_scitex_clew):
    # Arrange
    fake_scitex_clew.verify_claim = lambda claim_id_or_location: "verified"
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["details"] == {}




def test_reverify_clew_raises_returns_500_with_message__assert_response_status_code_500(client, env_snapshot, fake_scitex_clew):
    # Arrange
    def angry(claim_id_or_location):
        raise RuntimeError("claim not found in clew DAG")
    fake_scitex_clew.verify_claim = angry
    _pin(BUNDLE_ACCEPTED)
    # Act
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_z"}),
        content_type="application/json",
    )
    # Assert
    assert response.status_code == 500


def test_reverify_clew_raises_returns_500_with_message__assert_body_ok_is_false_3(client, env_snapshot, fake_scitex_clew):
    # Arrange
    def angry(claim_id_or_location):
        raise RuntimeError("claim not found in clew DAG")
    fake_scitex_clew.verify_claim = angry
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_z"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert body["ok"] is False


def test_reverify_clew_raises_returns_500_with_message__assert_claim_not_found_in_body_e(client, env_snapshot, fake_scitex_clew):
    # Arrange
    def angry(claim_id_or_location):
        raise RuntimeError("claim not found in clew DAG")
    fake_scitex_clew.verify_claim = angry
    _pin(BUNDLE_ACCEPTED)
    response = client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_z"}),
        content_type="application/json",
    )
    # Act
    body = json.loads(response.content)
    # Assert
    assert "claim not found" in body["error"]




def test_reverify_calls_clew_with_claim_id_positionally_only__assert_captured_called_is_true(client, env_snapshot, fake_scitex_clew):
    # clew's real signature is verify_claim(claim_id_or_location) — a SINGLE
    # positional arg. The handler must NOT pass against=/bundle_root=.
    # Arrange
    captured: dict = {}
    def recorder(claim_id_or_location):
        captured["arg"] = claim_id_or_location
        captured["called"] = True
        return {"claim": {"status": "verified"}}
    fake_scitex_clew.verify_claim = recorder
    _pin(BUNDLE_ACCEPTED)
    # Act
    client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Assert
    assert captured["called"] is True


def test_reverify_calls_clew_with_claim_id_positionally_only__assert_captured_arg_claim_a(client, env_snapshot, fake_scitex_clew):
    # clew's real signature is verify_claim(claim_id_or_location) — a SINGLE
    # positional arg. The handler must NOT pass against=/bundle_root=.
    # Arrange
    captured: dict = {}
    def recorder(claim_id_or_location):
        captured["arg"] = claim_id_or_location
        captured["called"] = True
        return {"claim": {"status": "verified"}}
    fake_scitex_clew.verify_claim = recorder
    _pin(BUNDLE_ACCEPTED)
    # Act
    client.post(
        "/api/claim/verify",
        data=json.dumps({"claim_id": "claim_a"}),
        content_type="application/json",
    )
    # Assert
    assert captured["arg"] == "claim_a"




# ──────────────────────────────────────────────────────────────────
# HANDLERS registration
# ──────────────────────────────────────────────────────────────────


def test_handlers_registry_includes_api_claim_verify():
    # Arrange
    from scitex_live_paper._django.handlers import HANDLERS, handle_reverify
    # Act
    # Assert
    assert HANDLERS["api/claim/verify"] is handle_reverify
