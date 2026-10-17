"""Port-backed endpoints — ``api/port/<port>/<target>``.

The dispatcher routes the ``api/port/`` prefix here (see
:func:`views.api_dispatch`); static endpoints stay in
:data:`HANDLERS`. The registry arrives on
``request.live_paper_context.renderers`` — handed in by the host's
resolver-built :class:`BundleContext`. No context (standalone
without injected adapters) or an empty registry raises
:class:`PortNotFound`, which the dispatcher maps to a JSON 404.
Adapters also raise :class:`PortNotFound` for unknown targets —
one exception, one status, both directions.
"""

from __future__ import annotations

from typing import Any, Mapping

from ...ports._registry import PortNotFound
from ..services import get_request_bundle_state

_PORT_METHODS = {
    "figure": "render_figure",
    "snippet": "render_snippet",
    "claim-graph": "render_claim_graph",
}


def handle_port(request, port: str, target: str) -> Mapping[str, Any]:
    """Dispatch one port call to the injected adapter.

    Returns the adapter's JSON-plain fragment mapping verbatim.
    Raises :class:`PortNotFound` when no registry is injected, the
    port is unknown, or the adapter reports an unknown target.
    """
    context = getattr(request, "live_paper_context", None)
    registry = getattr(context, "renderers", None) if context else None
    if registry is None:
        raise PortNotFound(f"no adapters registered for port {port!r}")
    method_name = _PORT_METHODS.get(port)
    if method_name is None:
        raise PortNotFound(f"unknown port {port!r}")
    adapter = registry.resolve(port)
    method = getattr(adapter, method_name, None)
    if method is None:
        raise PortNotFound(
            f"adapter for port {port!r} has no {method_name}()"
        )
    state = get_request_bundle_state(request)
    options = request.GET.dict()
    result = method(state.bundle, target, options)
    if not isinstance(result, Mapping):
        raise TypeError(
            f"port {port!r} adapter returned {type(result).__name__}, "
            "expected a JSON-plain mapping"
        )
    return result
