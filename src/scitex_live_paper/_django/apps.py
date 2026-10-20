#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Django AppConfig for the scitex-live-paper viewer app.

Declares the SDK base through the package attribute path
(``app.embed.ScitexAppConfig``, stats/writer leaf shape) so the host's
source-only plugin certifier proves the base through the SDK package's
literal module-forward branches instead of the ``embed`` module's
try/except-merged namespace. The guard stays LOUD on purpose (hub
ruling 2026-08-18, same as scitex-scholar and scitex-stats): a
``try/except ImportError: use django.apps.AppConfig`` fallback would
silently stop being an SDK workspace app the moment scitex-sdk is
missing, so every SDK contract evaporates while everything downstream
still believes it is in force. ``scitex-sdk`` is a REQUIRED member of
the ``server`` extra, so a missing one is a broken install that must
fail where the cause is legible — hence the guard below re-raises
with the install hint instead of degrading.

The label is ``scitex_live_paper``: the manifest slug ``live-paper``
is what ``scitex-hub`` looks up when mounting this app under
``/apps/live-paper/``.
"""

try:
    from scitex_sdk import app as _sdk_app
except ImportError as exc:
    raise ImportError(
        "scitex_live_paper._django.apps needs scitex-sdk, which is not installed. "
        "Install the optional stack: pip install 'scitex-live-paper[server]'"
    ) from exc


class LivePaperConfig(_sdk_app.embed.ScitexAppConfig):
    """Live-paper viewer Django app."""

    name = "scitex_live_paper._django"
    label = "scitex_live_paper"
    verbose_name = "SciTeX Live Paper Viewer"


# EOF
