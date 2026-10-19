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


def test_leaf_source_tree_present():
    # Arrange
    modules = sorted(SRC_ROOT.rglob("*.py"))
    # Act
    count = len(modules)
    # Assert
    assert count > 0


def test_no_hub_imports_in_leaf_source():
    # Arrange — every leaf Python module
    modules = sorted(SRC_ROOT.rglob("*.py"))
    # Act — sweep import lines only (comments/docstrings may name the host)
    offenders = {
        str(p.relative_to(SRC_ROOT)): [
            line
            for line in p.read_text().splitlines()
            if _HUB_IMPORT.match(line)
        ]
        for p in modules
    }
    # Assert — SDK-only: zero hub imports
    assert {k: v for k, v in offenders.items() if v} == {}


def test_app_config_prefers_sdk_base_with_vanilla_fallback():
    # Arrange — expected base depends on whether scitex_app is installed
    import importlib.util

    from scitex_live_paper._django import apps as apps_mod

    if importlib.util.find_spec("scitex_app") is not None:
        from scitex_app._django import (  # type: ignore[import-not-found]
            ScitexAppConfig as ExpectedBase,
        )
    else:
        from django.apps import AppConfig as ExpectedBase
    # Act
    config = apps_mod.LivePaperConfig
    # Assert — prefers the SDK registry base, else vanilla (never hard-fails)
    assert issubclass(config, ExpectedBase)


def test_manifest_carries_registry_required_fields():
    # Arrange
    manifest_path = SRC_ROOT / "_django" / "manifest.json"
    required = ("name", "slug", "label", "version", "icon")
    manifest = json.loads(manifest_path.read_text())
    # Act
    missing = [field for field in required if not manifest.get(field)]
    # Assert — same required set scitex_app validates on
    assert missing == []


def _shells(client):
    # Arrange helper — fetch standalone + embed shells once per test.
    standalone = client.get("/").content.decode("utf-8")
    embedded = client.get("/?embed=1").content.decode("utf-8")
    return standalone, embedded


def test_manifest_category_is_hub_taxonomy_member():
    # Arrange
    manifest_path = SRC_ROOT / "_django" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    taxonomy = (
        "writing", "visualization", "data", "analysis",
        "reference", "utility", "social", "other",
    )
    # Act
    category = manifest.get("category")
    # Assert — hub falls back to `other` for anything outside the enum
    assert category in taxonomy


def test_manifest_accent_color_is_live_paper_token():
    # Arrange
    manifest_path = SRC_ROOT / "_django" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    # Act
    accent = manifest.get("accent_color")
    # Assert — identifier (not hex); hub maps it to --app-accent-<value>
    assert accent == "live-paper"


def test_standalone_shell_references_no_hub_namespace(client):
    # Arrange
    standalone, _ = _shells(client)
    # Act
    leaked = "scitex_hub" in standalone
    # Assert
    assert leaked is False


def test_embed_shell_references_no_hub_namespace(client):
    # Arrange
    _, embedded = _shells(client)
    # Act
    leaked = "scitex_hub" in embedded
    # Assert
    assert leaked is False


def test_standalone_shell_carries_api_base(client):
    # Arrange
    standalone, _ = _shells(client)
    # Act
    wired = 'data-api-base="/api/"' in standalone
    # Assert
    assert wired is True


def test_embed_shell_flags_embed_mode(client):
    # Arrange
    _, embedded = _shells(client)
    # Act
    flagged = 'data-embed-mode="1"' in embedded
    # Assert
    assert flagged is True
