"""STX-TQ tests for the anchored-comments provider.

``GET/POST /api/comments`` is the server half of Live Paper comments:
it validates anchored notes and stores them as
``live-paper-comments.json`` in the pinned bundle directory.

Real Django test Client + a tmp COPY of the fixture bundle (the POST
writes into the bundle directory — the in-tree fixture must never be
dirtied). No ``monkeypatch``, no ``mock.patch``.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Iterator

import pytest

pytest.importorskip("django")

from django.test import Client  # noqa: E402

from scitex_live_paper._django import services  # noqa: E402
from scitex_live_paper._django.handlers import HANDLERS  # noqa: E402
from scitex_live_paper._django.handlers.comments import (  # noqa: E402
    COMMENTS_FILENAME,
    COMMENTS_SCHEMA,
)

FIXTURE_BUNDLE = Path(__file__).resolve().parents[2] / "fixtures" / "bundle-min"


@pytest.fixture
def scratch_bundle(tmp_path) -> Iterator[Path]:
    """Copy the fixture bundle to tmp + pin it for the test."""
    previous = os.environ.get("SCITEX_LIVE_PAPER_BUNDLE")
    target = tmp_path / "bundle"
    shutil.copytree(FIXTURE_BUNDLE, target)
    os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = str(target)
    services.clear_cache()
    try:
        yield target
    finally:
        if previous is not None:
            os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = previous
        else:
            os.environ.pop("SCITEX_LIVE_PAPER_BUNDLE", None)
        services.clear_cache()


@pytest.fixture
def client() -> Client:
    return Client()


def test_handler_registered(client, scratch_bundle):
    assert HANDLERS["api/comments"] is not None


def test_get_empty_before_any_post(client, scratch_bundle):
    response = client.get("/api/comments")
    assert response.status_code == 200
    payload = json.loads(response.content)
    assert payload == {"schema": COMMENTS_SCHEMA, "comments": [], "count": 0}


def test_post_claim_anchored_comment_roundtrip(client, scratch_bundle):
    response = client.post(
        "/api/comments",
        data=json.dumps(
            {
                "comment": {
                    "body": "verify against the new run",
                    "target": {"claim_id": "claim_a1b2c3d4e5f6"},
                    "author": "yw",
                }
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 200
    stored = json.loads(response.content)["comment"]
    assert stored["body"] == "verify against the new run"
    assert stored["target"] == {"claim_id": "claim_a1b2c3d4e5f6"}
    assert stored["author"] == "yw"
    assert stored["id"].startswith("c_") and stored["created_at"]

    sidecar = json.loads((scratch_bundle / COMMENTS_FILENAME).read_text())
    assert sidecar["schema"] == COMMENTS_SCHEMA
    assert len(sidecar["comments"]) == 1

    listed = json.loads(client.get("/api/comments").content)
    assert listed["count"] == 1 and listed["comments"][0]["id"] == stored["id"]


def test_post_region_and_quote_anchors(client, scratch_bundle):
    region = client.post(
        "/api/comments",
        data=json.dumps(
            {"comment": {"body": "axis?", "target": {"page": 3, "bbox": [1, 2, 3, 4]}}}
        ),
        content_type="application/json",
    )
    assert region.status_code == 200
    quote = client.post(
        "/api/comments",
        data=json.dumps({"comment": {"body": "agrees", "target": {"quote": "p<0.05"}}})
    ,
        content_type="application/json",
    )
    assert quote.status_code == 200
    assert json.loads(client.get("/api/comments").content)["count"] == 2


def test_post_rejects_bad_shapes(client, scratch_bundle):
    bad_bodies = [
        {},
        {"comment": {"body": "  ", "target": {"claim_id": "c"}}},
        {"comment": {"body": "x"}},
        {"comment": {"body": "x", "target": {"claim_id": "a", "quote": "b"}}},
        {"comment": {"body": "x", "target": {"page": 0, "bbox": [1, 2, 3]}}},
        "not-json{{{",
    ]
    for bad in bad_bodies:
        data = bad if isinstance(bad, str) else json.dumps(bad)
        response = client.post(
            "/api/comments", data=data, content_type="application/json"
        )
        assert response.status_code == 400, bad
    assert not (scratch_bundle / COMMENTS_FILENAME).exists()


def test_non_post_non_get_rejected(client, scratch_bundle):
    response = client.put(
        "/api/comments", data="{}", content_type="application/json"
    )
    assert response.status_code == 405
