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


@pytest.mark.parametrize("use_sessions", [False, True])
@pytest.mark.parametrize("embed", [False, True])
def test_native_comment_csrf_accepts_dom_token_and_refuses_unsafe_origins(
    isolated_comment_bundle, use_sessions, embed
):
    middleware = list(settings.MIDDLEWARE)
    if "django.middleware.csrf.CsrfViewMiddleware" not in middleware:
        middleware.append("django.middleware.csrf.CsrfViewMiddleware")
    if use_sessions:
        middleware.insert(0, "django.contrib.sessions.middleware.SessionMiddleware")
    with override_settings(
        MIDDLEWARE=middleware,
        CSRF_USE_SESSIONS=use_sessions,
        CSRF_COOKIE_HTTPONLY=True,
        SESSION_ENGINE="django.contrib.sessions.backends.signed_cookies",
        ALLOWED_HOSTS=["testserver"],
        CSRF_TRUSTED_ORIGINS=[],
    ):
        client = Client(enforce_csrf_checks=True)
        response = client.get("/?embed=1" if embed else "/")
        assert response.status_code == 200
        match = re.search(
            r'<meta name="live-paper-csrf-token" content="([^\"]+)"',
            response.content.decode(),
        )
        assert match and len(match[1]) == 64
        token = match[1]
        body = {
            "comment": {
                "body": "Disposable native CSRF fixture",
                "target": {"claim_id": "fixture-claim"},
            }
        }
        sidecar = isolated_comment_bundle / "live-paper-comments.json"
        missing = client.post(
            "/api/comments",
            data=json.dumps(body),
            content_type="application/json",
            HTTP_ORIGIN="http://testserver",
        )
        assert missing.status_code == 403
        assert not sidecar.exists()
        foreign = client.post(
            "/api/comments",
            data=json.dumps(body),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="http://evil.example",
        )
        assert foreign.status_code == 403
        assert not sidecar.exists()
        accepted = client.post(
            "/api/comments",
            data=json.dumps(body),
            content_type="application/json",
            HTTP_X_CSRFTOKEN=token,
            HTTP_ORIGIN="http://testserver",
        )
        assert accepted.status_code == 200
        assert accepted.json()["comment"]["body"] == body["comment"]["body"]
        assert (
            json.loads(sidecar.read_text())["comments"][0]["body"]
            == body["comment"]["body"]
        )
        listed = client.get("/api/comments")
        assert listed.json()["count"] == 1
