"""STX-TQ tests for the CCT 3000 archive-sidecar server persist.

``POST /api/event-log`` is the server half of the overlay event log:
it validates the ``event-log.js`` ``exportSidecar()`` shape and stores
it verbatim as ``live-paper-events.json`` in the pinned bundle
directory, so the archive keeps ``manuscript.pdf + event-log
sidecar`` on the server (not just as a client download).

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
from scitex_live_paper._django.handlers import handle_event_log  # noqa: E402

FIXTURE_BUNDLE = Path(__file__).resolve().parents[2] / "fixtures" / "bundle-min"

SIDECAR_SCHEMA = "scitex-live-paper.event-log/v1"
SIDECAR_FILENAME = "live-paper-events.json"


@pytest.fixture
def scratch_bundle(tmp_path) -> Iterator[Path]:
    """Copy the fixture bundle to tmp + pin it for the test.

    Saves/restores ``os.environ`` explicitly (no-mocks doctrine)
    with teardown that runs even when the test fails, so one test's
    pin never leaks into the next.
    """
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


def _sidecar(n_events: int = 2) -> dict:
    # Arrange
    # Act
    return {
        "schema": SIDECAR_SCHEMA,
        "exported_at": "2026-10-19T18:00:00+00:00",
        "bundle": None,
        "events": [
            {
                "ts": f"2026-10-19T18:00:0{i}+00:00",
                "kind": "live-paper:claim",
                "payload": {"claim_id": f"c{i}"},
            }
            for i in range(n_events)
        ],
    }
    # Assert


def _post(client, payload):
    # Arrange
    # Act
    if isinstance(payload, (dict, list)):
        body = json.dumps(payload)
    else:
        body = payload
    # Assert
    return client.post("/api/event-log", data=body, content_type="application/json")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_event_log_handler_registered():
    # Arrange
    # Act
    # Assert
    assert HANDLERS.get("api/event-log") is handle_event_log


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_post_valid_sidecar_returns_200(client, scratch_bundle):
    # Arrange
    # Act
    response = _post(client, _sidecar())
    # Assert
    assert response.status_code == 200


def test_post_valid_sidecar_receipt_ok(client, scratch_bundle):
    # Arrange
    # Act
    body = json.loads(_post(client, _sidecar()).content)
    # Assert
    assert body["ok"] is True


def test_post_valid_sidecar_receipt_schema(client, scratch_bundle):
    # Arrange
    # Act
    body = json.loads(_post(client, _sidecar()).content)
    # Assert
    assert body["schema"] == SIDECAR_SCHEMA


def test_post_valid_sidecar_receipt_event_count(client, scratch_bundle):
    # Arrange
    # Act
    body = json.loads(_post(client, _sidecar()).content)
    # Assert
    assert body["event_count"] == 2


def test_post_valid_sidecar_receipt_filename(client, scratch_bundle):
    # Arrange
    # Act
    body = json.loads(_post(client, _sidecar()).content)
    # Assert
    assert body["filename"] == SIDECAR_FILENAME


def test_post_valid_sidecar_receipt_received_at(client, scratch_bundle):
    # Arrange
    # Act
    body = json.loads(_post(client, _sidecar()).content)
    # Assert
    assert body["received_at"]


def test_post_valid_sidecar_writes_file(client, scratch_bundle):
    # Arrange
    # Act
    _post(client, _sidecar())
    # Assert
    assert (scratch_bundle / SIDECAR_FILENAME).is_file()


def test_post_valid_sidecar_stored_schema(client, scratch_bundle):
    # Arrange
    posted = _sidecar()
    # Act
    _post(client, posted)
    stored = json.loads((scratch_bundle / SIDECAR_FILENAME).read_text(encoding="utf-8"))
    # Assert
    assert stored["schema"] == posted["schema"]


def test_post_valid_sidecar_stored_events(client, scratch_bundle):
    # Arrange
    posted = _sidecar()
    # Act
    _post(client, posted)
    stored = json.loads((scratch_bundle / SIDECAR_FILENAME).read_text(encoding="utf-8"))
    # Assert
    assert stored["events"] == posted["events"]


def test_post_valid_sidecar_stored_exported_at(client, scratch_bundle):
    # Arrange
    posted = _sidecar()
    # Act
    _post(client, posted)
    stored = json.loads((scratch_bundle / SIDECAR_FILENAME).read_text(encoding="utf-8"))
    # Assert
    assert stored["exported_at"] == posted["exported_at"]


def test_post_twice_second_wins(client, scratch_bundle):
    # Arrange
    # Act
    _post(client, _sidecar(n_events=1))
    _post(client, _sidecar(n_events=3))
    stored = json.loads((scratch_bundle / SIDECAR_FILENAME).read_text(encoding="utf-8"))
    # Assert
    assert len(stored["events"]) == 3


def test_post_empty_events_list_returns_200(client, scratch_bundle):
    # Arrange
    # Act
    response = _post(client, _sidecar(n_events=0))
    # Assert
    assert response.status_code == 200


def test_post_empty_events_list_count_is_zero(client, scratch_bundle):
    # Arrange
    # Act
    body = json.loads(_post(client, _sidecar(n_events=0)).content)
    # Assert
    assert body["event_count"] == 0


# ---------------------------------------------------------------------------
# Method + body validation
# ---------------------------------------------------------------------------


def test_get_returns_405(client, scratch_bundle):
    # Arrange
    # Act
    response = client.get("/api/event-log")
    # Assert
    assert response.status_code == 405


def test_post_empty_body_returns_400(client, scratch_bundle):
    # Arrange
    # Act
    response = client.post("/api/event-log", data="", content_type="application/json")
    # Assert
    assert response.status_code == 400


def test_post_malformed_json_returns_400(client, scratch_bundle):
    # Arrange
    # Act
    response = _post(client, "{not json")
    # Assert
    assert response.status_code == 400


def test_post_json_list_returns_400(client, scratch_bundle):
    # Arrange
    # Act
    response = _post(client, [1, 2, 3])
    # Assert
    assert response.status_code == 400


def test_post_wrong_schema_returns_400(client, scratch_bundle):
    # Arrange
    payload = _sidecar()
    payload["schema"] = "scitex-live-paper.event-log/v9"
    # Act
    response = _post(client, payload)
    # Assert
    assert response.status_code == 400


def test_post_missing_schema_returns_400(client, scratch_bundle):
    # Arrange
    payload = _sidecar()
    del payload["schema"]
    # Act
    response = _post(client, payload)
    # Assert
    assert response.status_code == 400


def test_post_missing_events_returns_400(client, scratch_bundle):
    # Arrange
    payload = _sidecar()
    del payload["events"]
    # Act
    response = _post(client, payload)
    # Assert
    assert response.status_code == 400


def test_post_events_not_a_list_returns_400(client, scratch_bundle):
    # Arrange
    payload = _sidecar()
    payload["events"] = {"kind": "live-paper:claim"}
    # Act
    response = _post(client, payload)
    # Assert
    assert response.status_code == 400


def test_post_event_entry_not_a_mapping_returns_400(client, scratch_bundle):
    # Arrange
    payload = _sidecar()
    payload["events"] = ["live-paper:claim"]
    # Act
    response = _post(client, payload)
    # Assert
    assert response.status_code == 400


def test_rejected_post_writes_no_file(client, scratch_bundle):
    # Arrange
    payload = _sidecar()
    payload["schema"] = "wrong"
    # Act
    _post(client, payload)
    # Assert
    assert not (scratch_bundle / SIDECAR_FILENAME).exists()


# ---------------------------------------------------------------------------
# event-log.js client persist helper (static contract — the JS runs in
# the browser; here we pin the shape the browser relies on)
# ---------------------------------------------------------------------------


def _js_file() -> Path:
    import scitex_live_paper

    pkg_root = Path(scitex_live_paper.__file__).resolve().parent
    return pkg_root / "_django/static/live_paper/js/event-log.js"


def test_event_log_exports_persist_sidecar():
    # Arrange
    # Act
    text = _js_file().read_text(encoding="utf-8")
    # Assert
    assert "export async function persistSidecar" in text


def test_event_log_persist_uses_post_method():
    # Arrange
    # Act
    text = _js_file().read_text(encoding="utf-8")
    # Assert
    assert 'method: "POST"' in text


def test_event_log_persist_posts_to_event_log_endpoint():
    # Arrange
    # Act
    text = _js_file().read_text(encoding="utf-8")
    # Assert
    assert '+ "event-log"' in text
