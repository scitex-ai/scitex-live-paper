"""Cutover-bar audit pins for the leaf ``_django`` (SDK-only, no hub coupling).

Figrecipe cutover model (CCT-2784): the leaf owns its surface and the
host mounts it. Leaf-side rules pinned here:

1. No module under ``src/scitex_live_paper/`` imports ``scitex_hub``
   (or a bare ``hub`` package) — the leaf is SDK-only and boots
   without scitex-hub installed.
2. ``LivePaperConfig`` prefers ``scitex_app``'s ``ScitexAppConfig``
   (manifest registry) when installed, else falls back to vanilla
   Django ``AppConfig`` — the skeleton boots standalone either way.
3. ``manifest.json`` carries the registry-required fields
   (``name`` / ``slug`` / ``label`` / ``version`` / ``icon``).
4. Rendered viewer shells reference no ``scitex_hub`` URLs/namespaces —
   host mount points arrive via ``BundleContext.api_base`` + the
   ``data-api-base`` attribute, never via hub URL reversing.

``old-direct`` dev-only parity + mount dedupe are hub-side at
integration time (hub-owned per 2026-10-16 lane confirmation) and are
NOT pinned here. Unknown-endpoint / DOI 404 rules are pinned in
``test_dispatcher.py`` / ``test_doi_landing.py``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytest.importorskip("django")

LEGACY_DJANGO_DIR = Path(__file__).resolve().parent
SRC_ROOT = LEGACY_DJANGO_DIR.parents[2] / "src" / "scitex_live_paper"

# Import statements naming the hub (attribute/string mentions in docs,
# manifest metadata, and entry-point group names are NOT imports).
_HUB_IMPORT = re.compile(
    r"^\s*(?:from\s+(?:scitex_hub|hub)\b|import\s+(?:scitex_hub|hub)\b)",
    re.MULTILINE,
)


def test_no_hub_imports_in_leaf_source():
    # arrange — every leaf Python module
    modules = sorted(SRC_ROOT.rglob("*.py"))
    assert modules, "leaf src tree missing"
    # act — sweep import lines only (comments/docstrings may name the host)
    offenders = {
        str(p.relative_to(SRC_ROOT)): [
            line
            for line in p.read_text().splitlines()
            if _HUB_IMPORT.match(line)
        ]
        for p in modules
    }
    offenders = {k: v for k, v in offenders.items() if v}
    # assert — SDK-only: zero hub imports
    assert not offenders, f"hub imports in leaf: {offenders}"


def test_app_config_prefers_sdk_base_with_vanilla_fallback():
    # arrange
    from scitex_live_paper._django import apps as apps_mod

    # act
    config = apps_mod.LivePaperConfig
    # assert — prefers the SDK registry base when scitex_app is present,
    # otherwise falls back to vanilla Django AppConfig (never hard-fails)
    try:
        from scitex_app._django import (  # type: ignore[import-not-found]
            ScitexAppConfig,
        )

        assert issubclass(config, ScitexAppConfig)
    except ImportError:
        from django.apps import AppConfig

        assert issubclass(config, AppConfig)


def test_manifest_carries_registry_required_fields():
    # arrange
    manifest_path = SRC_ROOT / "_django" / "manifest.json"
    # act
    manifest = json.loads(manifest_path.read_text())
    # assert — same required set scitex_app validates on
    for field in ("name", "slug", "label", "version", "icon"):
        assert manifest.get(field), field


def test_viewer_shells_reference_no_hub_namespace(client):
    # arrange — standalone shell + embed shell (query-string lever)
    # act
    standalone = client.get("/").content.decode("utf-8")
    embedded = client.get("/?embed=1").content.decode("utf-8")
    # assert — no hub URL namespace leaks; host mount arrives via
    # BundleContext.api_base -> data-api-base only
    assert "scitex_hub" not in standalone
    assert "scitex_hub" not in embedded
    assert 'data-api-base="/api/"' in standalone
    assert 'data-embed-mode="1"' in embedded
