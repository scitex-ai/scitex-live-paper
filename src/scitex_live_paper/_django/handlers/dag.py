"""``api/dag`` — bundle DAG mermaid source for the SPA DAG pane.

Returns the bundle's ``dag.mmd`` string verbatim (the same source the
static ``dag.html`` renderer paints). The SPA renders it with the
vendored mermaid bundle and highlights the selected claim node.
Missing ``dag.mmd`` → JSON 404 so the pane hides itself instead of
rendering an empty graph.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

try:
    from django.http import JsonResponse
except ImportError as exc:
    raise ImportError(
        "scitex-live-paper's Django surface requires Django — "
        "install with: pip install 'scitex-live-paper[all]'"
    ) from exc

from scitex_live_paper._renderer.dag import graph_to_mermaid
from scitex_live_paper.evidence import find_claim

from .._evidence_files import ResourceError
from .._evidence_request import request_evidence
from ..services import get_request_bundle_state

__all__ = ["handle_dag"]


def handle_dag(request) -> JsonResponse:
    """Serve the selected claim's evidence, or the legacy bundle graph."""
    claim_id = request.GET.get("claim_id")
    if claim_id:
        try:
            _, packet = request_evidence(request)
        except ResourceError as error:
            if error.status != 404:
                return JsonResponse({"error": str(error)}, status=error.status)
        else:
            entry = find_claim(packet, claim_id)
            graph = entry and entry.get("graph")
            if graph is None:
                return JsonResponse({"error": "No evidence graph for this claim."}, status=404)
            mermaid, _ = graph_to_mermaid(graph, state=entry["state"], claim_type=entry.get("claim_type"))
            references = [
                {
                    "id": f"n{index}",
                    "node_id": node["id"],
                    "label": node["label"],
                    "kind": node["kind"],
                    "script_file": (node["script"].get("file")
                                    if isinstance(node.get("script"), Mapping) else None),
                }
                for index, node in enumerate(graph["nodes"])
                if node["kind"] in {"input", "output", "process"}
            ]
            return _graph_response({
                "mermaid": mermaid,
                "present": True,
                "scope": "claim",
                "provider": packet["provider"]["name"],
                "state": entry["state"],
                "reason": entry["reason"],
                "references": references,
            })

    state = get_request_bundle_state(request)
    mermaid = (state.bundle.dag or "").strip()
    if not mermaid:
        return JsonResponse({"error": "no dag.mmd in bundle"}, status=404)
    return _graph_response({"mermaid": mermaid, "present": True, "scope": "bundle"})


def _graph_response(payload: dict[str, Any]) -> JsonResponse:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    response = JsonResponse({**payload, "graph_sha256": hashlib.sha256(encoded).hexdigest()})
    response["Cache-Control"] = "private, no-store"
    return response
