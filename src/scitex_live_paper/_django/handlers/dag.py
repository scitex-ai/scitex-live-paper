"""``api/dag`` — bundle DAG mermaid source for the SPA DAG pane.

Returns the bundle's ``dag.mmd`` string verbatim (the same source the
static ``dag.html`` renderer paints). The SPA renders it with the
vendored mermaid bundle and highlights the selected claim node.
Missing ``dag.mmd`` → JSON 404 so the pane hides itself instead of
rendering an empty graph.
"""

from __future__ import annotations

from typing import Any, Mapping

try:
    from django.http import JsonResponse
except ImportError as exc:
    raise ImportError(
        "scitex-live-paper's Django surface requires Django — "
        "install with: pip install 'scitex-live-paper[all]'"
    ) from exc

from ..services import get_request_bundle_state

__all__ = ["handle_dag"]


def handle_dag(request) -> Mapping[str, Any]:
    """Return ``{"mermaid": <dag.mmd>}`` or a JSON 404 when absent."""
    state = get_request_bundle_state(request)
    mermaid = (state.bundle.dag or "").strip()
    if not mermaid:
        return JsonResponse({"error": "no dag.mmd in bundle"}, status=404)
    return {"mermaid": mermaid, "present": True}
