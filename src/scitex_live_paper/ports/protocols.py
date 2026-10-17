"""Port ``Protocol``s — the injection points of the neutral core.

Three ports; each takes the loaded :class:`Bundle` plus a target id
and returns a JSON-plain mapping (never a Django response — the
dispatcher wraps). A port method that cannot serve its target returns
``{"error": ...}``; the dispatcher maps that to the documented HTTP
status (404 unknown target, 500 adapter failure). Adapters raise
only for programmer errors.

Port names (registry keys): ``"figure"``, ``"snippet"``,
``"claim-graph"``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Mapping, Protocol, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from ..bundle import Bundle

#: Registry keys for the three ports.
FIGURE_PORT = "figure"
SNIPPET_PORT = "snippet"
CLAIM_GRAPH_PORT = "claim-graph"

PORT_NAMES = (FIGURE_PORT, SNIPPET_PORT, CLAIM_GRAPH_PORT)


@runtime_checkable
class FigurePort(Protocol):
    """Re-render one live figure from its data/code blob."""

    def render_figure(
        self,
        bundle: Bundle,
        figure_id: str,
        options: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...


@runtime_checkable
class SnippetPort(Protocol):
    """Render an HTML/code snippet for hover evidence."""

    def render_snippet(
        self,
        bundle: Bundle,
        ref: str,
        options: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...


@runtime_checkable
class ClaimGraphPort(Protocol):
    """Render the claim subgraph around one claim."""

    def render_claim_graph(
        self,
        bundle: Bundle,
        claim_id: str,
        options: Mapping[str, Any],
    ) -> Mapping[str, Any]: ...
