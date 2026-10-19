"""Consumer conformance kit for port adapters (distribution half of §5).

Third-party hosts (journal, hub PDF viewer, writer/_django,
scholar/_django) implement the §2 port ``Protocol``s in their own
packages and prove it by calling these checks in their own suites —
one green run per consumer is the integration gate. The core NEVER
imports a consumer; the checks import only the neutral surface.
"""

from __future__ import annotations

from typing import Any, Mapping, Tuple

from .protocols import (
    CLAIM_GRAPH_PORT,
    FIGURE_PORT,
    PORT_NAMES,
    SNIPPET_PORT,
)

#: Port name → the single render method its adapter must expose.
RENDER_METHOD = {
    FIGURE_PORT: "render_figure",
    SNIPPET_PORT: "render_snippet",
    CLAIM_GRAPH_PORT: "render_claim_graph",
}


def check_entry_point(entry: Any) -> Tuple[str, str, Any]:
    """Validate an entry-point payload per the :func:`discover` contract."""
    port = entry.port
    assert port in PORT_NAMES, f"unknown port {port!r}"
    name = getattr(entry, "name", "default")
    assert isinstance(name, str) and name, "entry name must be a non-empty str"
    adapter = entry.adapter
    method = RENDER_METHOD[port]
    render = getattr(adapter, method, None)
    assert callable(render), f"{type(adapter).__name__} lacks {method}()"
    return port, name, adapter


def check_figure_fragment(
    fragment: Mapping[str, Any], figure_id: str
) -> Mapping[str, Any]:
    """Validate a figure-port result envelope (figure_id/title/html/provenance)."""
    assert fragment["figure_id"] == figure_id
    assert fragment["title"] == f"figure:{figure_id}"
    assert isinstance(fragment["html"], str) and fragment["html"]
    provenance = fragment["provenance"]
    assert isinstance(provenance, list) and provenance
    for link in provenance:
        assert link["label"] and link["href"]
    return fragment
