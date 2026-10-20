"""Port-backed endpoints — ``api/port/<port>/<target>``.

The dispatcher routes the ``api/port/`` prefix here (see
:func:`views.api_dispatch`); static endpoints stay in
:data:`HANDLERS`. The registry arrives on
``request.live_paper_context.renderers`` — handed in by the host's
resolver-built context, or attached empty by the standalone-serve
middleware. No context at all raises :class:`PortNotFound`, which
the dispatcher maps to a JSON 404. Adapters also raise
:class:`PortNotFound` for unknown targets — one exception, one
status, both directions.

The bundled default figure adapter (``FigzFigureAdapter``) is
registered on demand whenever no explicit ``"figure"`` adapter is
present — hosts keep theirs, standalone gets one for free.
"""

from __future__ import annotations

from typing import Any, Mapping

from ...ports import FigzFigureAdapter, Registry
from ...ports._registry import PortNotFound
from ..services import get_request_bundle_state, resolve_bundle_path
from scitex_live_paper import BundleContext, BundleSource


def _standalone_context_from_env() -> "BundleContext | None":
    """Ephemeral port context over the env-pinned bundle, or None.

    The SDK ``run_standalone`` server (and any host that skips the
    serve-context middleware) leaves ``request.live_paper_context``
    unset. When ``SCITEX_LIVE_PAPER_BUNDLE`` is pinned, synthesize
    the same context the middleware would have attached: env bundle
    + a registry the dispatcher back-fills with bundled defaults.
    Env unset (or not a directory) → None, and the caller keeps the
    pinned 404.
    """
    try:
        bundle_path = resolve_bundle_path()
    except RuntimeError:
        return None
    if not bundle_path.is_dir():
        return None
    return BundleContext(
        source=BundleSource.from_directory(bundle_path),
        renderers=Registry(),
    )

_PORT_METHODS = {
    "figure": "render_figure",
    "snippet": "render_snippet",
    "claim-graph": "render_claim_graph",
}


def handle_port(request, port: str, target: str) -> Mapping[str, Any]:
    """Dispatch one port call to the injected adapter.

    Returns the adapter's JSON-plain fragment mapping verbatim.
    Raises :class:`PortNotFound` when there is no context at all, the
    port is unknown, or the adapter reports an unknown target. A
    present-but-adapterless context gets the bundled default figure
    adapter — :meth:`Registry.resolve` then decides per port.

    Standalone (no mount/middleware context, e.g. the SDK
    ``run_standalone`` server whose middleware list is fixed): when
    the ``SCITEX_LIVE_PAPER_BUNDLE`` env pin is set, an ephemeral
    context over that bundle with the bundled defaults is
    synthesized, so the viewer works out of the box. With neither a
    context nor an env pin (bare unit-test request), the pinned 404
    stands.
    """
    context = getattr(request, "live_paper_context", None)
    registry = getattr(context, "renderers", None) if context else None
    if registry is None:
        if context is None:
            context = _standalone_context_from_env()
            if context is None:
                # No context at all (bare unit-test request, host
                # bypassing mount/middleware): nothing to inject
                # into — pinned 404.
                raise PortNotFound("no adapters registered")
            registry = context.renderers
        else:
            registry = Registry()
    assert registry is not None  # narrowed: both branches yield a Registry
    if "figure" not in registry.ports:
        # Standalone + minimal host contexts get the bundled default
        # figure adapter: the mount() signature stays unchanged and
        # port calls work out of the box. Hosts that inject their own
        # "figure" adapter keep it — we never override an explicit
        # registration.
        registry.register("figure", FigzFigureAdapter())
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
