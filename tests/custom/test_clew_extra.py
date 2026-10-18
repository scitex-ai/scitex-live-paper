"""Tests for the ``[clew]`` optional dependency extra.

Pins the contract that ``pip install scitex-live-paper[clew]`` pulls
``scitex-clew``, and that the M2 re-verify endpoints' fallback reason
strings name the extra so the operator can copy the install command
straight out of the SPA badge.

Real file IO against ``pyproject.toml`` — no mocks.
"""

from __future__ import annotations

import re
from importlib.metadata import PackageNotFoundError, metadata
from pathlib import Path

try:
    import tomllib  # py3.11+
except ImportError:  # pragma: no cover - py3.10 fallback
    import tomli as tomllib  # type: ignore[no-redef]


def _pyproject() -> dict:
    root = Path(__file__).resolve().parents[2]
    return tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))


# ──────────────────────────────────────────────────────────────────
# pyproject.toml — the canonical declaration
# ──────────────────────────────────────────────────────────────────


def test_clew_extra_is_declared_in_pyproject():
    # Arrange
    # Act
    extras = _pyproject()["project"]["optional-dependencies"]
    # Assert
    assert "clew" in extras, "[clew] extra missing from pyproject.toml"


def test_clew_extra_pulls_scitex_clew():
    # Arrange
    # Act
    extras = _pyproject()["project"]["optional-dependencies"]
    clew_deps = extras["clew"]
    # Assert
    assert any("scitex-clew" in dep for dep in clew_deps), (
        f"[clew] extra must pull scitex-clew; got {clew_deps!r}"
    )


def test_clew_extra_pins_minimum_version():
    # Arrange
    # Act
    extras = _pyproject()["project"]["optional-dependencies"]
    clew_deps = extras["clew"]
    # Assert
    assert any(re.search(r"scitex-clew\s*>=", dep) for dep in clew_deps), (
        f"[clew] extra must pin a minimum version; got {clew_deps!r}"
    )


def test_existing_extras_preserved():
    # Regression — adding [clew] must not drop the other extras
    # Arrange
    # Act
    extras = _pyproject()["project"]["optional-dependencies"]
    # Assert
    for required in ("django", "mcp", "test"):
        assert required in extras, f"{required!r} extra disappeared"


# ──────────────────────────────────────────────────────────────────
# Installed metadata — the runtime view (best-effort)
# ──────────────────────────────────────────────────────────────────


def test_clew_extra_visible_in_installed_metadata():
    # Some editable-install paths don't materialise extras into the
    # installed metadata; treat this as advisory rather than blocking.
    # Arrange
    try:
        meta = metadata("scitex-live-paper")
    except PackageNotFoundError:
        return
    requires_dist = meta.get_all("Requires-Dist") or []
    # Act
    has_clew_extra = any(
        "extra == 'clew'" in dep or 'extra == "clew"' in dep
        for dep in requires_dist
    )
    # Assert
    if requires_dist:
        assert has_clew_extra, (
            f"installed metadata has Requires-Dist but no clew extra: {requires_dist!r}"
        )


# ──────────────────────────────────────────────────────────────────
# Fallback reason strings name the extra
# ──────────────────────────────────────────────────────────────────


def _verify_payload_with_clew_hidden():
    """POST /api/claim/verify with ``scitex_clew`` made unimportable.

    Shared Arrange+Act for the no-clew fallback tests (each test keeps a
    single assert per STX-TQ007).
    """
    import os
    import json as _json
    import sys as _sys
    from pathlib import Path as _Path

    import pytest

    pytest.importorskip("django")

    from django.test import Client
    from scitex_live_paper._django import services

    # Ensure clew isn't importable for the duration of this assertion.
    key = "scitex_clew"
    sentinel = object()
    original = _sys.modules.get(key, sentinel)
    _sys.modules[key] = None  # type: ignore[assignment]
    try:
        bundle = _Path(__file__).resolve().parents[2] / "tests" / "scitex_live_paper" / "fixtures" / "bundle-accepted"
        snap = dict(os.environ)
        try:
            os.environ["SCITEX_LIVE_PAPER_BUNDLE"] = str(bundle)
            services.clear_cache()

            response = Client().post(
                "/api/claim/verify",
                data=_json.dumps({"claim_id": "claim_a1b2c3d4e5f6"}),
                content_type="application/json",
            )
            return _json.loads(response.content)
        finally:
            for k in list(os.environ):
                if k not in snap:
                    del os.environ[k]
            for k, v in snap.items():
                os.environ[k] = v
    finally:
        if original is sentinel:
            _sys.modules.pop(key, None)
        else:
            _sys.modules[key] = original  # type: ignore[assignment]


def test_reverify_no_clew_falls_back__assert_payload_fallback_is_true():
    """``api/claim/verify`` falls back (fallback=True) without clew."""
    # Arrange
    # Act
    payload = _verify_payload_with_clew_hidden()
    # Assert
    assert payload["fallback"] is True


def test_reverify_no_clew_reason_names_install_command():
    """``api/claim/verify`` falls back with a reason naming the [clew] extra."""
    # Arrange
    # Act
    payload = _verify_payload_with_clew_hidden()
    # Assert
    assert "scitex-live-paper[clew]" in payload["reason"], (
        f"fallback reason must name [clew] extra; got {payload['reason']!r}"
    )
