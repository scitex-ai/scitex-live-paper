"""``api/comments`` — minimal anchored-comments provider (prompt-10 item 4).

Live Paper is the provider of rich PDF + overlay + comments + ports.
Overlay and ports already exist; comments land here: anchored notes
consumers (writer, agentic-journal) and readers attach to a claim, a
PDF region, or a quoted passage.

Endpoints
---------
``GET /api/comments``
    List the bundle's comments:: ``{schema, comments: [...], count}``.
    No sidecar yet → ``comments: []`` (HTTP 200, never 404).
``POST /api/comments``
    Append one comment. Body must be a mapping with a ``comment``
    mapping::

        {"comment": {"body": "...", "target": {"claim_id": "..."},
                     "author": "...", "kind": "..."}}

    ``body`` (non-empty string) and ``target`` are required.
    ``target`` takes exactly one anchor shape:

    - ``{"claim_id": "<id>"}``
    - ``{"page": <1-based int>, "bbox": [x0, y0, x1, y1]}``
    - ``{"quote": "<passage>"}``

    ``author`` / ``kind`` are optional strings. The server stamps
    ``id`` (``c_<uuid8>``) and ``created_at`` (UTC ISO-8601).

Comments persist as ``live-paper-comments.json`` in the pinned bundle
directory (same sidecar convention as the event-log handler): an
envelope ``{schema: "scitex-live-paper.comments/v1", comments: [...]}``
written on every POST. The bundle cache invalidates on
``claims.json`` mtime only, so sidecar writes never thrash it.
"""

from __future__ import annotations

import datetime
import json
import uuid
from typing import Any, Mapping

import scitex_logging as slogging

try:
    from django.http import HttpResponse, JsonResponse
except ImportError as exc:  # pragma: no cover - defensive
    raise ImportError(
        "scitex-live-paper's Django surface requires Django — "
        "install with: pip install 'scitex-live-paper[server]'"
    ) from exc

from ..services import get_request_bundle_state

log = slogging.getLogger(__name__)

__all__ = [
    "COMMENTS_SCHEMA",
    "COMMENTS_FILENAME",
    "handle_comments",
    "validate_comment",
]

#: Pinned sidecar schema.
COMMENTS_SCHEMA = "scitex-live-paper.comments/v1"

#: Sidecar filename inside the bundle directory.
COMMENTS_FILENAME = "live-paper-comments.json"


def _utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _is_bbox(value: Any) -> bool:
    return (
        isinstance(value, (list, tuple))
        and len(value) == 4
        and all(isinstance(n, (int, float)) for n in value)
    )


def validate_comment(candidate: Any) -> tuple[Mapping[str, Any] | None, str | None]:
    """Validate a posted comment mapping.

    Returns ``(stored_fields, None)`` on success — the caller stamps
    ``id`` / ``created_at`` — or ``(None, error_message)``.
    """
    if not isinstance(candidate, Mapping):
        return None, "'comment' must be a JSON object"
    body = candidate.get("body")
    if not isinstance(body, str) or not body.strip():
        return None, "'comment.body' is required and must be a non-empty string"
    target = candidate.get("target")
    if not isinstance(target, Mapping):
        return None, "'comment.target' is required and must be a JSON object"
    claim_id = target.get("claim_id")
    page = target.get("page")
    bbox = target.get("bbox")
    quote = target.get("quote")
    shapes = [
        isinstance(claim_id, str) and bool(claim_id.strip()),
        isinstance(page, int)
        and not isinstance(page, bool)
        and page >= 1
        and _is_bbox(bbox),
        isinstance(quote, str) and bool(quote.strip()),
    ]
    if sum(bool(s) for s in shapes) != 1:
        return (
            None,
            "'comment.target' needs exactly one anchor: "
            "{claim_id} | {page, bbox} | {quote}",
        )
    for key in ("author", "kind"):
        if key in candidate and not isinstance(candidate[key], str):
            return None, f"'comment.{key}' must be a string when present"
    stored: dict[str, Any] = {
        "body": body.strip(),
        "target": dict(target),
    }
    for key in ("author", "kind"):
        if isinstance(candidate.get(key), str) and candidate[key].strip():
            stored[key] = candidate[key].strip()
    return stored, None


def _read_sidecar(request) -> list[dict[str, Any]]:
    state = get_request_bundle_state(request)
    path = state.bundle_path / COMMENTS_FILENAME
    if not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(payload, Mapping):
        return []
    if payload.get("schema") != COMMENTS_SCHEMA:
        return []
    comments = payload.get("comments")
    if not isinstance(comments, list):
        return []
    return [dict(c) for c in comments if isinstance(c, Mapping)]


def _write_sidecar(request, comments: list[dict[str, Any]]) -> None:
    state = get_request_bundle_state(request)
    path = state.bundle_path / COMMENTS_FILENAME
    path.write_text(
        json.dumps({"schema": COMMENTS_SCHEMA, "comments": comments}, indent=2) + "\n",
        encoding="utf-8",
    )


def handle_comments(request) -> HttpResponse:
    """List (GET) or append (POST) anchored comments."""
    if request.method == "GET":
        comments = _read_sidecar(request)
        return JsonResponse(
            {"schema": COMMENTS_SCHEMA, "comments": comments, "count": len(comments)}
        )
    if request.method != "POST":
        return JsonResponse(
            {"error": "method not allowed; use GET to list, POST to add"},
            status=405,
        )
    body = _parse_json_body(request)
    if not isinstance(body, Mapping):
        return JsonResponse(
            {"error": "request body must be a JSON object"},
            status=400,
        )
    stored, error = validate_comment(body.get("comment"))
    if error is not None:
        return JsonResponse({"error": error}, status=400)
    assert stored is not None
    comment = {
        "id": f"c_{uuid.uuid4().hex[:8]}",
        "created_at": _utcnow(),
        **stored,
    }
    comments = _read_sidecar(request)
    comments.append(comment)
    _write_sidecar(request, comments)
    log.info("[comments] stored %s (%d total)", comment["id"], len(comments))
    return JsonResponse({"ok": True, "comment": comment, "count": len(comments)})


def _parse_json_body(request) -> Any:
    """Lenient JSON body parser. Returns ``None`` on empty / malformed."""
    if not request.body:
        return None
    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return None
