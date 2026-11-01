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


def test_comments_handler_is_registered(client, scratch_bundle):
    # Arrange
    # Act
    handler = HANDLERS["api/comments"]
    # Assert
    assert callable(handler)


def test_get_empty_before_any_post(client, scratch_bundle):
    # Arrange
    # Act
    response = client.get("/api/comments")
    # Assert
    assert (response.status_code, json.loads(response.content)) == (
        200,
        {"schema": COMMENTS_SCHEMA, "comments": [], "count": 0},
    )


def test_post_claim_anchored_comment_roundtrip(client, scratch_bundle):
    # Arrange
    comment = {
        "body": "verify against the new run",
        "target": {"claim_id": "claim_a1b2c3d4e5f6"},
        "author": "yw",
    }
    # Act
    response = client.post(
        "/api/comments",
        data=json.dumps({"comment": comment}),
        content_type="application/json",
    )
    stored = json.loads(response.content)["comment"]
    sidecar = json.loads((scratch_bundle / COMMENTS_FILENAME).read_text())
    listed = json.loads(client.get("/api/comments").content)
    # Assert
    assert (
        response.status_code,
        {k: stored[k] for k in comment},
        stored["id"].startswith("c_"),
        bool(stored["created_at"]),
        sidecar["schema"],
        sidecar["comments"],
        listed["count"],
        listed["comments"],
    ) == (200, comment, True, True, COMMENTS_SCHEMA, [stored], 1, [stored])


@pytest.mark.parametrize(
    "target", [{"page": 3, "bbox": [1, 2, 3, 4]}, {"quote": "p<0.05"}]
)
def test_post_region_quote_anchor_roundtrip(client, scratch_bundle, target):
    # Arrange
    comment = {"body": "check this", "target": target}
    # Act
    response = client.post(
        "/api/comments",
        data=json.dumps({"comment": comment}),
        content_type="application/json",
    )
    listed = json.loads(client.get("/api/comments").content)
    # Assert
    assert (response.status_code, listed["count"], listed["comments"][0]["target"]) == (
        200,
        1,
        target,
    )


@pytest.mark.parametrize(
    "bad",
    [
        {},
        {"comment": {"body": "  ", "target": {"claim_id": "c"}}},
        {"comment": {"body": "x"}},
        {"comment": {"body": "x", "target": {"claim_id": "a", "quote": "b"}}},
        {"comment": {"body": "x", "target": {"page": 0, "bbox": [1, 2, 3]}}},
        "not-json{{{",
    ],
)
def test_post_rejects_bad_comment_shapes(client, scratch_bundle, bad):
    # Arrange
    data = bad if isinstance(bad, str) else json.dumps(bad)
    # Act
    response = client.post("/api/comments", data=data, content_type="application/json")
    # Assert
    assert (
        response.status_code == 400
        and not (scratch_bundle / COMMENTS_FILENAME).exists()
    )


def test_non_post_non_get_rejected(client, scratch_bundle):
    # Arrange
    # Act
    response = client.put("/api/comments", data="{}", content_type="application/json")
    # Assert
    assert response.status_code == 405
