"""Root URLconf for the standalone live-paper server.

Mounts the app at root (``""``). Under hub mount (M3) this file is *not*
used — the hub does ``include("scitex_live_paper._django.urls")`` under
``/viewer-v2/`` itself.
"""

from __future__ import annotations

try:
    from django.urls import include, path
except ImportError as exc:
    raise ImportError(
        "scitex-live-paper's Django surface requires Django — "
        "install with: pip install 'scitex-live-paper[all]'"
    ) from exc

urlpatterns = [
    path("", include("scitex_live_paper._django.urls")),
]
