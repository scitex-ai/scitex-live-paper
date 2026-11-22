"""Bounded inline previews for files identified by an authorized claim graph."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path

from scitex_live_paper.evidence import find_claim

from .._evidence_files import ResourceError, ResourceReader
from .._evidence_request import request_evidence
from .._preview_formats import format_preview, read_limit
from .evidence_pages import _response

_DIGEST = re.compile(r"(?:sha256:)?([0-9a-f]{32}|[0-9a-f]{64})", re.IGNORECASE)


def _preview(root: Path, entry: Mapping, node_id: str, *, start: int, member: int | None) -> dict:
    node = next(
        (node for node in (entry.get("graph") or {}).get("nodes", []) if node["id"] == node_id),
        None,
    )
    if node is None:
        raise ResourceError("Evidence node not found.", 404)
    if node["kind"] == "process":
        script = node.get("script")
        if not isinstance(script, Mapping):
            raise ResourceError("The run has no recorded script available for preview.", 404)
        name, digest = script.get("file"), script.get("hash")
    elif node["kind"] in {"input", "output"} and not node.get("external"):
        name, digest = node["label"], node.get("hash")
    else:
        raise ResourceError("This evidence node has no project file available for preview.", 404)
    if not isinstance(name, str) or not name or Path(name).is_absolute():
        raise ResourceError("This evidence file is outside the project.", 403)
    match = _DIGEST.fullmatch(digest) if isinstance(digest, str) else None
    if match is None:
        raise ResourceError("A comparable file hash was not recorded.", 409)
    with ResourceReader(root) as reader:
        content = reader.read(name, limit=read_limit(name))
    expected = match.group(1).lower()
    if hashlib.sha256(content).hexdigest()[:len(expected)] != expected:
        raise ResourceError("The current file differs from the recorded evidence.", 409)
    return {
        "file": name, "hash": digest, "size": len(content),
        **format_preview(name, content, start, member),
    }


def handle_evidence_preview(request):
    def respond(data, status=200):
        return _response(json.dumps(data), status=status, content_type="application/json")

    if request.method not in {"GET", "HEAD"}:
        response = respond({"error": "Method not allowed."}, 405)
        response["Allow"] = "GET, HEAD"
        return response
    claim_id, node_id = request.GET.get("claim_id"), request.GET.get("node_id")
    if not claim_id or not node_id:
        return respond({"error": "A claim ID and node ID are required."}, 400)
    start, member = request.GET.get("start", "0"), request.GET.get("member")
    if any(
        len(value) > 10 or not value.isascii() or not value.isdecimal()
        for value in (start, member) if value is not None
    ):
        return respond({"error": "Invalid preview window or member."}, 400)
    try:
        root, packet = request_evidence(request)
        entry = find_claim(packet, claim_id)
        if entry is None:
            raise ResourceError("Registered claim not found.", 404)
        return respond(_preview(
            root, entry, node_id, start=int(start),
            member=int(member) if member is not None else None,
        ))
    except ResourceError as error:
        return respond({"error": str(error)}, error.status)
