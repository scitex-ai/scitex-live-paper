---
description: |
  [TOPIC] Runtime environment variables
  [DETAILS] Standalone bundle pinning and Django settings actually read by LivePaper.
tags: [scitex-live-paper-env-vars]
---

# Runtime environment variables

The standalone server/settings read these values; mounted hosts own their
Django configuration and per-request resolver instead.

| Variable | Source behavior |
| --- | --- |
| `SCITEX_LIVE_PAPER_BUNDLE` | Bundle directory pinned for standalone requests; `serve` sets it from its argument. |
| `SCITEX_LIVE_PAPER_ALLOWED_HOSTS` | Additional comma-separated allowed host names for standalone Django. |
| `SCITEX_LIVE_PAPER_DJANGO_SECRET` | Optional stable Django secret; absent uses a random process-local value. |
| `SCITEX_LIVE_PAPER_APP_MODE` | Standalone settings mode; defaults to `standalone`. |
| `DJANGO_DEBUG` | Shared legacy setting; only the string `true` enables debug. |

See `_django/_server.py`, `_django/settings.py`, and `_django/services.py`.
Never log secret values or replace host authorization with environment paths.
A process-wide bundle pin is unsuitable as shared multi-user project selection.
