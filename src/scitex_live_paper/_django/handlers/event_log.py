"""``api/event-log`` — archive-sidecar server persist (CCT 3000).

The browser collects the overlay session into an event-log sidecar
(``event-log.js`` ``exportSidecar()``: ``{schema, exported_at, bundle,
events}``) and could only download it client-side. This handler is the
server half: it validates the posted sidecar and stores it as
``live-paper-events.json`` inside the pinned bundle directory, so the
archive keeps ``manuscript.pdf + event-log sidecar`` on the server and
an overlay session can be replayed later.

Schema ownership: the ``scitex-live-paper.event-log/v1`` shape is
authored by the ``event-log.js`` client module. This handler pins the
schema string + filename as constants and validates structure only
(mapping body, exact schema match, ``events`` a list of mappings) —
it never re-documents or extends the event payload schema.

The stored file is written VERBATIM from the validated body so the
archived sidecar is byte-identical to what the client's
``downloadSidecar()`` would save. The bundle cache
(``services.get_bundle_state``) invalidates on ``claims.json`` mtime
only, so the sidecar write never thrashes it, and ``bundle.load``
reads named files — the extra sibling is ignored.
"""

from __future__ import annotations

import datetime
import json
from typing import Any, Mapping

import scitex_logging as slogging

try:
    from django.http import HttpResponse, JsonResponse
except ImportError as exc:
    raise ImportError(
        "scitex-live-paper's Django surface requires Django — "
        "install with: pip install 'scitex-live-paper[server]'"
    ) from exc

from ..services import get_request_bundle_state

log = slogging.getLogger(__name__)

__all__ = ["SIDECAR_SCHEMA", "SIDECAR_FILENAME", "handle_event_log"]

#: Pinned sidecar schema — must match ``event-log.js`` ``exportSidecar``.
SIDECAR_SCHEMA = "scitex-live-paper.event-log/v1"

#: Archive filename — matches the client ``downloadSidecar`` default so
#: the server-persisted and client-downloaded sidecars share one name.
SIDECAR_FILENAME = "live-paper-events.json"


def handle_event_log(request) -> HttpResponse:
    """Persist a posted event-log sidecar into the bundle directory.

    Request
    -------
    ``POST /api/event-log``
    Body (JSON) — the ``exportSidecar()`` shape::

        {
            "schema":      "scitex-live-paper.event-log/v1",  # required, exact
            "exported_at": "<ISO-8601>",                      # passthrough
            "bundle":      {...} | null,                      # passthrough
            "events":      [{"ts": ..., "kind": ..., "payload": {...}}, ...]
        }

    Response
    --------
    On success::

        {
            "ok": true,
            "schema": "scitex-live-paper.event-log/v1",
            "event_count": <int>,
            "filename": "live-paper-events.json",
            "received_at": "<ISO-8601 server stamp>"
        }

    Error cases:

    - Non-POST → 405 with ``{"error": "method not allowed"}``
    - Missing / non-mapping body → 400
    - Schema mismatch → 400
    - ``events`` missing / not a list / entry not a mapping → 400
    """
    if request.method != "POST":
        return JsonResponse(
            {"error": "method not allowed; POST a JSON body"},
            status=405,
        )

    body = _parse_json_body(request)
    if not isinstance(body, Mapping):
        return JsonResponse(
            {"error": "request body must be a JSON object"},
            status=400,
        )

    if body.get("schema") != SIDECAR_SCHEMA:
        return JsonResponse(
            {
                "error": (
                    f"'schema' must be {SIDECAR_SCHEMA!r}, "
                    f"got {body.get('schema')!r}"
                )
            },
            status=400,
        )

    events = body.get("events")
    if not isinstance(events, list):
        return JsonResponse(
            {"error": "'events' is required and must be a list"},
            status=400,
        )
    for entry in events:
        if not isinstance(entry, Mapping):
            return JsonResponse(
                {"error": "every entry in 'events' must be a JSON object"},
                status=400,
            )

    state = get_request_bundle_state(request)
    sidecar_path = state.bundle_path / SIDECAR_FILENAME
    # Verbatim store: the archived sidecar is byte-identical to what
    # the client's downloadSidecar() saves (replay fidelity).
    sidecar_path.write_text(
        json.dumps(dict(body), indent=2) + "\n",
        encoding="utf-8",
    )
    log.info(
        "[event-log] stored %d events to %s",
        len(events),
        sidecar_path,
    )

    return JsonResponse(
        {
            "ok": True,
            "schema": SIDECAR_SCHEMA,
            "event_count": len(events),
            "filename": SIDECAR_FILENAME,
            "received_at": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
        }
    )


def _parse_json_body(request) -> Any:
    """Lenient JSON body parser. Returns ``None`` on empty / malformed."""
    if not request.body:
        return None
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return None
