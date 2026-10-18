"""Django test bootstrap for the live-paper skeleton.

Skips the whole package when Django is not installed (the base install
ships without it). Otherwise: pin the test settings module, run
``django.setup()``, and hand out a Django ``Client`` plus a
``bundle_env`` fixture that pins the in-tree fixture bundle for the
duration of each test.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytest.importorskip("django")

import django  # noqa: E402 - import after importorskip
from django.test import Client  # noqa: E402

os.environ.setdefault(
    "DJANGO_SETTINGS_MODULE",
    "scitex_live_paper._django.settings",
)
django.setup()

FIXTURE_BUNDLE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "bundle-min"
)


@pytest.fixture
def bundle_env():
    """Pin ``SCITEX_LIVE_PAPER_BUNDLE`` to the in-tree fixture and clear cache.

    Saves/restores ``os.environ`` explicitly (no-mocks doctrine: no
    ``monkeypatch`` fixture) with teardown that runs even when the test
    fails, so one test's pin never leaks into the next.
    """
    from scitex_live_paper._django import services

    # Arrange
    previous = os.environ.get("SCITEX_LIVE_PAPER_BUNDLE")
    os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = str(FIXTURE_BUNDLE)
    services.clear_cache()
    try:
        # Act
        yield FIXTURE_BUNDLE
    finally:
        # Teardown (assert-neutral): restore prior env + clear cache
        if previous is not None:
            os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = previous
        else:
            os.environ.pop("SCITEX_LIVE_PAPER_BUNDLE", None)
        services.clear_cache()


@pytest.fixture
def client() -> Client:
    """Django test client — no auth, no session."""
    return Client()
