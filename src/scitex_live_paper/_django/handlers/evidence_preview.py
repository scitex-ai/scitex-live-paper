"""Bounded inline previews for files identified by an authorized claim graph."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from collections.abc import Mapping
from pathlib import Path

from scitex_live_paper.evidence import find_claim

from .._evidence_files import ResourceError, ResourceReader
from .._evidence_request import request_evidence
from .evidence_pages import _response

_MAX_FILE = 512 * 1024
_MAX_TEXT = 16_000
_DIGEST = re.compile(r"(?:sha256:)?([0-9a-f]{32}|[0-9a-f]{64})", re.IGNORECASE)
_TEXT = frozenset({
    ".csv", ".ini", ".ipynb", ".json", ".jsonl", ".md", ".py", ".r", ".sh",
    ".tex", ".toml", ".tsv", ".txt", ".yaml", ".yml",
})
_IMAGES = {".png": "image/png", ".jpeg": "image/jpeg", ".jpg": "image/jpeg"}


def _preview(root: Path, entry: Mapping, node_id: str) -> dict:
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
    suffix = Path(name).suffix.lower()
    if suffix not in _TEXT and suffix not in _IMAGES:
        raise ResourceError("Inline preview is unavailable for this file format.", 415)
    with ResourceReader(root) as reader:
        content = reader.read(name, limit=_MAX_FILE)
    expected = match.group(1).lower()
    if hashlib.sha256(content).hexdigest()[:len(expected)] != expected:
        raise ResourceError("The current file differs from the recorded evidence.", 409)
    payload = {"file": name, "hash": digest}
    if suffix in _IMAGES:
        return {
            **payload, "kind": "image", "media_type": _IMAGES[suffix],
            "data": base64.b64encode(content).decode("ascii"),
        }
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        raise ResourceError("This evidence file is not UTF-8 text.", 415) from None
    return {**payload, "kind": "text", "text": text[:_MAX_TEXT], "truncated": len(text) > _MAX_TEXT}


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
    try:
        root, packet = request_evidence(request)
        entry = find_claim(packet, claim_id)
        if entry is None:
            raise ResourceError("Registered claim not found.", 404)
        return respond(_preview(root, entry, node_id))
    except ResourceError as error:
        return respond({"error": str(error)}, error.status)
