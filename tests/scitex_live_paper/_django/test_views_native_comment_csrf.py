"""Real Django CSRF policy around native comment dispatch, temp bundles only."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client, override_settings

from scitex_live_paper._django import services


@pytest.fixture
def isolated_comment_bundle(tmp_path):
    source = Path(__file__).resolve().parents[1] / "fixtures/bundle-min"
    target = tmp_path / "bundle"
    shutil.copytree(source, target)
    previous = os.environ.get("SCITEX_LIVE_PAPER_BUNDLE")
    os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = str(target)
    services.clear_cache()
    try:
        yield target
    finally:
        if previous is None:
            os.environ.pop("SCITEX_LIVE_PAPER_BUNDLE", None)
        else:
            os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = previous
        services.clear_cache()


@pytest.fixture(params=[False, True], ids=["httponly-cookie", "session-token"])
def csrf_transport(request):
    return request.param


@pytest.fixture(params=[False, True], ids=["full", "embed"])
def comment_client(isolated_comment_bundle, csrf_transport, request):
    middleware = list(settings.MIDDLEWARE)
    if "django.middleware.csrf.CsrfViewMiddleware" not in middleware:
        middleware.append("django.middleware.csrf.CsrfViewMiddleware")
    if csrf_transport:
        middleware.insert(0, "django.contrib.sessions.middleware.SessionMiddleware")
    with override_settings(
        MIDDLEWARE=middleware,
        CSRF_USE_SESSIONS=csrf_transport,
        CSRF_COOKIE_HTTPONLY=True,
        SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies",
        ALLOWED_HOSTS=["testserver"],
        CSRF_TRUSTED_ORIGINS=[],
    ):
        client = Client(enforce_csrf_checks=True)
        response = client.get("/?embed=1" if request.param else "/")
        match = re.search(
            r'<meta name="live-paper-csrf-token" content="([^\"]+)"',
            response.content.decode(),
        )
        token = match[1] if match else ""
        yield client, token, response.status_code


@pytest.fixture
def comment_body():
    return {
        "comment": {
            "body": "Disposable native CSRF fixture",
            "target": {"claim_id": "fixture-claim"},
        }
    }


def test_native_comment_page_exposes_usable_dom_csrf_token(comment_client):
    # Arrange
    _client, token, page_status = comment_client
    # Act
    observed = page_status, len(token)
    # Assert
    assert observed == (200, 64)


@pytest.mark.parametrize(
    "foreign_origin", [False, True], ids=["missing-token", "foreign-origin"]
)
def test_native_comment_refuses_unsafe_post_without_persistence(
    comment_client, isolated_comment_bundle, comment_body, foreign_origin
):
    # Arrange
    client, token, _status = comment_client
    headers = {
        False: {"HTTP_ORIGIN": "http://testserver"},
        True: {"HTTP_ORIGIN": "http://evil.example", "HTTP_X_CSRFTOKEN": token},
    }[foreign_origin]
    sidecar = isolated_comment_bundle / "live-paper-comments.json"
    # Act
    response = client.post(
        "/api/comments",
        data=json.dumps(comment_body),
        content_type="application/json",
        **headers,
    )
    # Assert
    assert (response.status_code, sidecar.exists()) == (403, False)


def test_native_comment_accepts_dom_token_and_reloads_persisted_body(
    comment_client, isolated_comment_bundle, comment_body
):
    # Arrange
    client, token, _status = comment_client
    sidecar = isolated_comment_bundle / "live-paper-comments.json"
    expected_body = comment_body["comment"]["body"]
    # Act
    response = client.post(
        "/api/comments",
        data=json.dumps(comment_body),
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
        HTTP_ORIGIN="http://testserver",
    )
    listed = client.get("/api/comments")
    observed = (
        response.status_code,
        response.json()["comment"]["body"],
        json.loads(sidecar.read_text())["comments"][0]["body"],
        listed.json()["count"],
    )
    # Assert
    assert observed == (200, expected_body, expected_body, 1)
