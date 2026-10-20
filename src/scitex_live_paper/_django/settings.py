"""Minimal standalone Django settings for ``scitex-live-paper serve``.

Used only by the standalone launcher and the test suite; cloud
deployments ignore this module and mount
``scitex_live_paper._django.urls`` under their own prefix.

Mirrors the ``scitex_scholar._django.settings`` pattern: bare-minimum
installed apps, ``scitex_sdk.ui`` for the shared workspace shell, DEBUG
defaulting to false with the ALLOWED_HOSTS switch (operator ruling,
2026-08-23).

Deviation from scholar (deliberate): ``DATABASES`` stays empty.
Live-paper is an engine over bundle files on disk — it declares no
models, and every handler reads the bundle off disk or delegates to
scitex-clew, which owns its own store. Django's dummy backend makes
any accidental ORM call fail loudly instead of silently succeeding
against a scratch database nothing else would ever read.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Fleet env-var convention is SCITEX_LIVE_PAPER_<X>.
SECRET_KEY = os.environ.get("SCITEX_LIVE_PAPER_DJANGO_SECRET") or secrets.token_urlsafe(32)
# DEBUG DEFAULTS TO FALSE (scholar 2026-09-02): a default-true DEBUG
# made the permissive ALLOWED_HOSTS="*" branch the default, and
# DEBUG=False stops runserver serving static files — answered here
# by _standalone_urls.py, which serves them through the staticfiles
# finders regardless of DEBUG.
DEBUG = os.environ.get("DJANGO_DEBUG", "false").lower() == "true"
# ALLOWED_HOSTS SWITCHES ON DEBUG (operator ruling, 2026-08-23).
# DEBUG=True  -> "*". Explicit opt-in for development only.
# DEBUG=False -> loopback + `--host` contribution (see _server.py) +
# SCITEX_LIVE_PAPER_ALLOWED_HOSTS (proxy DNS / tailnet names).
if DEBUG:
    ALLOWED_HOSTS = ["*"]
else:
    ALLOWED_HOSTS = ["127.0.0.1", "localhost", "0.0.0.0", "testserver"]
    _extra_hosts = os.environ.get("SCITEX_LIVE_PAPER_ALLOWED_HOSTS", "")
    ALLOWED_HOSTS += [h.strip() for h in _extra_hosts.split(",") if h.strip()]

# "hub" | "standalone" — the browser tab alone must distinguish the
# two (fleet convention). These settings only boot the STANDALONE
# server (`scitex-live-paper serve`), so standalone is the default.
SCITEX_APP_MODE = os.environ.get("SCITEX_LIVE_PAPER_APP_MODE", "standalone")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "scitex_live_paper._django.apps.LivePaperConfig",
]

# scitex-sdk supplies the shared workspace shell that
# `viewer.html` extends. It is a REQUIRED member of the `server`
# extra (alongside django itself), so it is not optional AT RUN
# TIME — but it IS optional for the DISTRIBUTION, so the import is
# GUARDED and the guard FAILS LOUDLY. A silent guard would swallow
# a broken install and resurface it later as a TemplateDoesNotExist
# pointing at scitex-sdk's template.
try:
    import scitex_sdk.ui  # noqa: F401
except ImportError as exc:  # scitex-sdk absent — the [server]-gated GUI capability only
    raise ImportError(
        "scitex_live_paper._django.settings needs scitex-sdk, which is not "
        "installed. Install the optional stack: pip install 'scitex-live-paper[server]'"
    ) from exc

INSTALLED_APPS.append("scitex_sdk.ui")

# scitex-sdk ships `scitex_sdk/app/app_shell.html`, the base template
# viewer.html EXTENDS. APP_DIRS only searches installed apps, so
# leaving scitex_sdk.app out of INSTALLED_APPS makes every page 500
# with `TemplateDoesNotExist: scitex_sdk/app/app_shell.html` (stats
# hit exactly this; same loud-guard rationale as above).
try:
    import scitex_sdk.app  # noqa: F401
except ImportError as exc:  # scitex-sdk absent — the [server]-gated GUI capability only
    raise ImportError(
        "scitex_live_paper._django.settings needs scitex-sdk app, which is not "
        "installed. Install the optional stack: pip install 'scitex-live-paper[server]'"
    ) from exc

INSTALLED_APPS.append("scitex_sdk.app")

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    # Standalone serve only (hub/hosts use their own settings): attach
    # the env-pinned bundle context when a request has none, so
    # api/port/* works out of the box with the bundled defaults.
    "scitex_live_paper._django.serve_context.LivePaperServeContextMiddleware",
]

ROOT_URLCONF = "scitex_live_paper._django._standalone_urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
            ],
        },
    },
]

# No database at all (see module docstring: engine over files on
# disk, no models). Django accepts an empty mapping and installs its
# dummy backend, so any accidental ORM call fails loudly here.
DATABASES: dict[str, dict[str, str]] = {}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

STATIC_URL = "/static/"
STATICFILES_DIRS: list[str] = [str(BASE_DIR / "static")]
