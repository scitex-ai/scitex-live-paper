"""Standalone server entry for ``scitex-live-paper serve``.

Pins the bundle path for the process via the ``SCITEX_LIVE_PAPER_BUNDLE``
env var (handlers read it through :func:`services.resolve_bundle_path`
when no mount context is present) and delegates to
``scitex_sdk.app.embed.run_standalone`` — the shared workspace shell,
so the local server looks like the mounted hub app (scholar pattern).

``scitex-sdk`` is an OPTIONAL dependency of the DISTRIBUTION
(``[server]``), not of THIS MODULE. :file:`_cli/serve.py` imports
:func:`serve` at command time, so this file sits on the console-script
launch path and must import with or without the GUI stack installed.
The capability is still not optional at RUN time: :func:`serve`
refuses with the extra's name rather than falling back to a
half-wired server (see the guards below).

Cloud deployments do NOT use this — they mount
``scitex_live_paper._django.urls`` into their own Django project.
"""

from __future__ import annotations

import os
from pathlib import Path

import scitex_logging as slogging

log = slogging.getLogger(__name__)

_DEFAULT_HOST = "127.0.0.1"
_DEFAULT_PORT = 8765

# The ONE install line every [server]-gated GUI-capability refusal names.
ALL_EXTRA_HINT = "pip install 'scitex-live-paper[server]'"

# GUARDED (scholar pattern, 2026-09-20): hard import would make
# `scitex-live-paper --version` fail on a bare install. The sentinels
# stay None and every RUN path that needs them refuses by name.
# Nothing is silently substituted.
try:
    from scitex_sdk import app as _sdk_app

    hosts_to_allow = _sdk_app.hosts_to_allow
    run_standalone = _sdk_app.embed.run_standalone
except ImportError:  # scitex-sdk absent — the [server] capability only
    hosts_to_allow = None  # type: ignore[assignment]
    run_standalone = None  # type: ignore[assignment]


def serve(
    bundle_path: str | Path,
    *,
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
    open_browser: bool = False,
) -> None:
    """Boot the standalone server pinned to ``bundle_path``.

    Sets ``SCITEX_LIVE_PAPER_BUNDLE`` (always overwritten — this *is*
    the contract), contributes the bind address to
    ``SCITEX_LIVE_PAPER_ALLOWED_HOSTS`` (scholar ``_server.run``
    pattern: binding to an address IS the statement you intend to be
    reached on it), then delegates to the SDK launcher. Blocks until
    the server is stopped (Ctrl-C).

    The ``run_standalone`` sentinel is read at CALL time (not import
    time) so tests can swap the module attribute with a real spy and
    restore it — no mocks, no runner kwarg.
    """
    resolved = Path(bundle_path).expanduser().resolve()
    if not resolved.is_dir():
        raise FileNotFoundError(
            f"bundle path is not a directory: {resolved}"
        )

    # Refuse BEFORE touching the environment: without the SDK there
    # is no shell and no ALLOWED_HOSTS derivation.
    if run_standalone is None or hosts_to_allow is None:
        raise ImportError(
            "The live-paper server needs scitex-sdk, which is not installed. "
            f"Install the optional stack: {ALL_EXTRA_HINT}"
        )

    os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = str(resolved)

    _contributed = hosts_to_allow(host)
    if _contributed:
        _configured = os.environ.get("SCITEX_LIVE_PAPER_ALLOWED_HOSTS", "")
        _hosts = [h.strip() for h in _configured.split(",") if h.strip()]
        for _h in _contributed:
            if _h not in _hosts:
                _hosts.append(_h)
        os.environ["SCITEX_LIVE_PAPER_ALLOWED_HOSTS"] = ",".join(_hosts)

    log.info(
        "[live-paper] serving %s on http://%s:%d/", resolved, host, port,
    )
    run_standalone(
        app_module="scitex_live_paper._django",
        port=port,
        host=host,
        open_browser=open_browser,
    )
