"""External-injection surface for the neutral core.

The core NEVER imports a renderer. Everything renderable arrives
through these three pieces:

- :mod:`scitex_live_paper.ports.protocols` — the three port
  ``Protocol``s (figure / snippet / claim-graph).
- :class:`Registry` — in-process port-to-adapter map (the mechanism).
- :class:`EventBus` / :class:`Event` — in-process fan-out; the DOM
  side mirrors it as ``CustomEvent("live-paper:<kind>")``.

Distribution rides the ``scitex.livepaper.renderers`` entry-point
group (:func:`discover`); direct-passing (``Registry.register``)
keeps tests and the standalone server free of packaging ceremony.
Full rationale in ``docs/dev/ports-events-contract.md``.
"""

from __future__ import annotations

from . import protocols
from ._bus import Event, EventBus
from ._discovery import discover
from ._figz_adapter import FigzFigureAdapter
from ._fragments import ProvenanceLink, figure_fragment, popup_fragment
from ._registry import PortNotFound, Registry

__all__ = [
    "protocols",
    "Event",
    "EventBus",
    "discover",
    "FigzFigureAdapter",
    "ProvenanceLink",
    "figure_fragment",
    "popup_fragment",
    "PortNotFound",
    "Registry",
]
