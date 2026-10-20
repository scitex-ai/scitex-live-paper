"""Root URLconf for the standalone live-paper server.

Mounts the app at root (``""``). Under hub mount this file is *not*
used — the hub does ``include("scitex_live_paper._django.urls")``
under ``/apps/live-paper/`` itself.

STATIC FILES ARE SERVED HERE REGARDLESS OF DEBUG (scholar pattern,
2026-09-02). Django's ``runserver`` serves /static/ only while
DEBUG=True; the SDK ``run_standalone`` launcher calls it with
``--insecure`` so static resolves either way, but the test suite
(leaf settings, DEBUG=False default) routes through THIS file — so
the staticfiles-finders serve below keeps the suite green without
re-opening ALLOWED_HOSTS="*".

Django is a `[server]`-extra member: not optional AT RUN TIME (this
module IS a urlconf), optional for the DISTRIBUTION — so the import
is GUARDED and the guard FAILS LOUDLY.
"""

from __future__ import annotations

try:
    from django.contrib.staticfiles.views import serve as _serve_static
    from django.urls import include, path, re_path
except ImportError as exc:  # django absent — the [server]-gated GUI capability only
    raise ImportError(
        "scitex_live_paper._django._standalone_urls needs Django, which is not "
        "installed. Install the optional stack: pip install 'scitex-live-paper[server]'"
    ) from exc

urlpatterns = [
    re_path(r"^static/(?P<path>.*)$", _serve_static, {"insecure": True}),
    path("", include("scitex_live_paper._django.urls")),
]
