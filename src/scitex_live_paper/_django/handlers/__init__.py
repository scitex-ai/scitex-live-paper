"""Handler registry for the live-paper SPA dispatcher.

The ``HANDLERS`` mapping is the *single source of truth* for what the
``<path:endpoint>`` catch-all in ``views.api_dispatch`` will route.

- ``api/ping``         — liveness probe
- ``api/bundle-info``  — bundle summary + paper_state
- ``api/claims``       — full claim list + re_verify_enabled flag (SPA sidebar)
- ``api/dashboard``    — merged boot payload (bundle-info + claims)
                         so the SPA can boot in one round-trip
- ``api/pdf``          — bundle manuscript PDF bytes (ported from
                         ``scitex_writer/_django/handlers/compile.py:handle_pdf``;
                         see ``docs/research/writer-pdf-viewer-findings.md``)
- ``api/dag``          — bundle ``dag.mmd`` mermaid source for the SPA
                         DAG pane (JSON 404 when the bundle ships none)
- ``api/claim/verify``  — M2 re-verify endpoint (calls ``scitex_clew.verify_claim``
                          against ``bundle.paper_state.pinned_commit``;
                          degrades gracefully when clew is not installed)
- ``api/claims/verify`` — M2 bulk re-verify (per-claim envelopes; one bad
                         claim doesn't 500 the sweep)
- ``api/event-log`` — CCT 3000 archive sidecar persist (POST a validated
                        ``scitex-live-paper.event-log/v1`` sidecar; stored
                        verbatim as ``live-paper-events.json`` in the bundle
                        directory next to ``manuscript.pdf``)
- ``api/comments``  — anchored-comments provider (GET lists the
                        ``live-paper-comments.json`` sidecar; POST appends
                        one validated comment anchored to a claim id,
                        a page+bbox region, or a quoted passage)

Extend this dict when new endpoints land; do NOT inline endpoint
logic in ``views.py``.
"""

from __future__ import annotations

from typing import Callable, Dict

from .claims import handle_claims
from .comments import handle_comments
from .core import bundle_info, ping
from .dag import handle_dag
from .dashboard import handle_dashboard
from .event_log import handle_event_log
from .pdf import handle_pdf
from .reverify import handle_reverify, handle_reverify_all

HandlerFn = Callable[..., object]

# fmt: off
HANDLERS: Dict[str, HandlerFn] = {
    "api/ping":           ping,
    "api/bundle-info":    bundle_info,
    "api/claims":         handle_claims,
    "api/dashboard":      handle_dashboard,
    "api/pdf":            handle_pdf,
    "api/dag":            handle_dag,
    "api/claim/verify":   handle_reverify,
    "api/claims/verify":  handle_reverify_all,
    "api/event-log":      handle_event_log,
    "api/comments":       handle_comments,
}
# fmt: on

__all__ = [
    "HANDLERS",
    "ping",
    "bundle_info",
    "handle_claims",
    "handle_dag",
    "handle_dashboard",
    "handle_event_log",
    "handle_pdf",
    "handle_reverify",
    "handle_reverify_all",
]
