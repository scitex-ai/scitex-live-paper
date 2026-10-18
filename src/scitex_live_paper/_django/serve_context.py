"""Standalone-serve bundle-context middleware (serve-defaults wiring).

Attached ONLY in the standalone ``settings.py`` MIDDLEWARE. Hub
mounts and host embeds use their own settings (or the
:func:`mount` wrapper) and are untouched by this module.

When a request arrives without ``live_paper_context`` and
``SCITEX_LIVE_PAPER_BUNDLE`` names a directory, attaches
``BundleContext(source=from_directory(...))`` so port dispatch
works in pure ``serve`` mode; :func:`services.get_request_bundle_state`
then injects the bundled default figure adapter exactly as it does
for minimal host contexts.

Set-if-absent: resolver-built (mount/host) contexts are never
clobbered — the ``getattr`` guard leaves them alone.
"""

from __future__ import annotations

import os
from typing import Any, Callable

from .._types import BundleContext, BundleSource

__all__ = ["LivePaperServeContextMiddleware"]


class LivePaperServeContextMiddleware:
    """Attach the env-pinned bundle context when a request has none."""

    def __init__(self, get_response: Callable[..., Any]) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        if getattr(request, "live_paper_context", None) is None:
            bundle_dir = os.environ.get("SCITEX_LIVE_PAPER_BUNDLE")
            if bundle_dir:
                request.live_paper_context = BundleContext(
                    source=BundleSource.from_directory(bundle_dir),
                )
        return self.get_response(request)
