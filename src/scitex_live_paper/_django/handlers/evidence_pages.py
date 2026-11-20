"""Serve the existing manuscript/evidence renderer through the authorized mount."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory

try:
    from django.conf import settings
    from django.http import HttpResponse
except ImportError as exc:
    raise ImportError("Evidence pages require scitex-live-paper[server]") from exc

from scitex_live_paper._renderer.dag import render_claim_graph
from scitex_live_paper._renderer.paper import render_paper
from scitex_live_paper.bundle import BundleMissingError
from scitex_live_paper.evidence import find_claim, review_text

from .._evidence_files import DEFAULT_MAX_TEXT_BYTES, ResourceError, ResourceReader
from .._evidence_request import request_evidence, resource_url

_CSP = (
    "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "connect-src 'self'; img-src 'self' data: blob:; font-src 'self'; "
    "base-uri 'none'; form-action 'none'; frame-ancestors 'self'"
)


def _response(body, *, status=200, content_type="text/html; charset=utf-8"):
    response = HttpResponse(body, status=status, content_type=content_type)
    response["Cache-Control"] = "private, no-store"
    response["Vary"] = "Cookie, Authorization"
    response["X-Content-Type-Options"] = "nosniff"
    response["Referrer-Policy"] = "same-origin"
    response["Content-Security-Policy"] = _CSP
    return response


def _page(request, kind):
    if request.method not in {"GET", "HEAD"}:
        response = _response("Method not allowed", status=405, content_type="text/plain")
        response["Allow"] = "GET, HEAD"
        return response
    try:
        root, packet = request_evidence(request)
        if kind == "review.json":
            return _response(json.dumps(packet), content_type="application/json")
        if kind == "review.txt":
            return _response(review_text(packet), content_type="text/plain; charset=utf-8")
        def asset(name):
            return resource_url(request, "assets", name=name)
        paper_url = resource_url(request, "paper.html")
        with TemporaryDirectory(prefix="live-paper-request-") as temporary:
            if kind == "graph.html":
                entry = find_claim(packet, request.GET.get("claim_id", ""))
                if entry is None:
                    raise ResourceError("Registered claim not found", 404)
                page = render_claim_graph(
                    entry, temporary, viewer_url=paper_url, claims_url=paper_url,
                    paper_url=paper_url, asset_url=asset,
                )
            else:
                limit = getattr(settings, "SCITEX_LIVE_PAPER_MAX_TEXT_BYTES", DEFAULT_MAX_TEXT_BYTES)
                with ResourceReader(root) as reader:
                    remaining = limit
                    def read_text(name):
                        nonlocal remaining
                        if type(remaining) is int and remaining <= 0:
                            raise ResourceError("Manuscript text exceeds its size limit", 413)
                        try:
                            content = reader.read(name, limit=remaining)
                            remaining -= len(content)
                            return content.decode("utf-8")
                        except UnicodeDecodeError:
                            raise ResourceError("Manuscript text must be UTF-8", 400) from None
                    result = render_paper(
                        packet, temporary, claims_url=paper_url,
                        read_text=read_text, asset_url=asset,
                    )
                if result is None:
                    raise ResourceError("No registered manuscript text is available", 404)
                page = result.paper_html
            return _response(page.read_bytes())
    except ResourceError as error:
        return _response(str(error), status=error.status, content_type="text/plain; charset=utf-8")
    except BundleMissingError:
        return _response("Paper bundle not found", status=404, content_type="text/plain")


def handle_paper(request):
    return _page(request, "paper.html")


def handle_graph(request):
    return _page(request, "graph.html")


def handle_review_json(request):
    return _page(request, "review.json")


def handle_review_text(request):
    return _page(request, "review.txt")


def handle_evidence_asset(request):
    """Only installed package assets are eligible; no author paths are served."""
    from scitex_sdk.ui import get_static_dir

    if request.method not in {"GET", "HEAD"}:
        response = _response("Method not allowed", status=405, content_type="text/plain")
        response["Allow"] = "GET, HEAD"
        return response
    renderer = Path(__file__).parents[2] / "_renderer" / "assets"
    assets = {"assets/" + name: renderer / name for name in (
        "claims.css", "support.css", "paper.css", "paper-panel.js", "paper.js",
        "dag.css", "dag.js", "mermaid/mermaid.min.js", "sdk-header-slot.js",
    )}
    assets.update({
        "assets/sdk-app-header.css": get_static_dir() / "css/app/app-header.css",
        "assets/sdk-app-header.js": get_static_dir() / "js/app/app-header.js",
    })
    path = assets.get(request.GET.get("name", ""))
    if path is None:
        return _response("Paper asset not found", status=404, content_type="text/plain")
    try:
        content = path.read_bytes()
    except OSError:
        return _response("Paper asset is unavailable", status=503, content_type="text/plain")
    content_type = "text/css" if path.suffix == ".css" else "text/javascript"
    return _response(content, content_type=content_type + "; charset=utf-8")
