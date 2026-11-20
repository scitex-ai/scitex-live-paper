"""Request-bound evidence snapshots and sibling resource URLs."""

from __future__ import annotations

import copy
import json
from collections.abc import Mapping

try:
    from django.conf import settings
except ImportError as exc:
    raise ImportError("Mounted evidence requires scitex-live-paper[server]") from exc

from scitex_live_paper.evidence import ContractError, build_review_packet, validate_report

from . import services
from ._evidence_files import DEFAULT_MAX_REPORT_BYTES, ResourceError, ResourceReader


def resource_url(request, endpoint: str, **parameters: str) -> str:
    """Retain host selectors on every page and owned asset request."""
    query = request.GET.copy()
    for key in ("claim_id", "name"):
        query.pop(key, None)
    for key, value in parameters.items():
        query[key] = value
    base = "/" + request.path.rsplit("/", 1)[0].lstrip("/")
    path = base.rstrip("/") + "/" + endpoint
    encoded = query.urlencode()
    return path + ("?" + encoded if encoded else "")


def request_evidence(request):
    """Copy a host snapshot or read the canonical report inside its bundle.

    The report's project_root is metadata, never a filesystem capability.
    No provider is invoked and the host's snapshot is never modified.
    """
    context = getattr(request, "live_paper_context", None)
    root = getattr(context, "resource_root", None)
    snapshot = getattr(context, "evidence_report", None)
    bundle = None
    if root is None or snapshot is None:
        bundle = services.get_request_bundle_state(request).bundle
    root = root if root is not None else bundle.root
    if snapshot is None:
        limit = getattr(settings, "SCITEX_LIVE_PAPER_MAX_REPORT_BYTES", DEFAULT_MAX_REPORT_BYTES)
        with ResourceReader(bundle.root) as reader:
            raw = reader.read("evidence-report.json", limit=limit)
        try:
            snapshot = json.loads(raw)
        except (UnicodeDecodeError, ValueError):
            raise ResourceError("Invalid evidence report JSON", 400) from None
    report = copy.deepcopy(snapshot)
    try:
        validate_report(report)
        for claim in report["claims"]:
            if not isinstance(claim["claim_id"], str) or not claim["claim_id"]:
                raise ValueError
            name = claim["location"].get("file")
            if name is not None and not isinstance(name, str):
                raise ValueError
            text = claim.get("stated_text")
            if text is not None and not isinstance(text, str):
                raise ValueError
            source = claim.get("source")
            if source is not None and not isinstance(source, Mapping):
                raise ValueError
        report["project_root"] = "."
        urls = {
            claim["claim_id"]: resource_url(request, "graph.html", claim_id=claim["claim_id"])
            for claim in report["claims"]
        }
        packet = build_review_packet(report, urls)
    except (ContractError, KeyError, TypeError, ValueError):
        raise ResourceError("Invalid evidence report contract", 400) from None
    return root, packet


def manuscript_url(request):
    """Offer the manuscript route when this authorized bundle has evidence."""
    from scitex_live_paper.bundle import BundleMissingError

    context = getattr(request, "live_paper_context", None)
    if getattr(request, "live_paper_empty_reason", None):
        return None
    if getattr(context, "evidence_report", None) is not None:
        return resource_url(request, "paper.html")
    if context is None:
        try:
            services.resolve_bundle_path()
        except RuntimeError:  # An unconfigured shell has no bundle to advertise.
            return None
    try:
        request_evidence(request)
    except BundleMissingError:
        return None
    except ResourceError as error:
        if error.status == 404:
            return None
        # A present, invalid or inaccessible report still has an actionable
        # route; opening it surfaces the precise refusal instead of hiding it.
    return resource_url(request, "paper.html")
