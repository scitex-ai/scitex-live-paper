"""Cutover-bar audit pins for the leaf ``_django`` (SDK-only, no hub coupling).

Figrecipe cutover model (CCT-2784): the leaf owns its surface and the
host mounts it. Leaf-side rules pinned here:

1. No module under ``src/scitex_live_paper/`` imports ``scitex_hub``
   (or a bare ``hub`` package) — the leaf is SDK-only and boots
   without scitex-hub installed.
2. ``LivePaperConfig`` subclasses ``scitex_sdk.app.embed.ScitexAppConfig``
   (stats/writer leaf shape) with a LOUD guard — no vanilla fallback
   (hub ruling 2026-08-18: a fallback silently drops every SDK contract).
3. ``manifest.json`` carries the registry-required fields
   (``name`` / ``slug`` / ``label`` / ``version`` / ``icon``) plus the
   mount fields (``scope`` / ``pip_package`` / ``mount_policy``).
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
    # Arrange — SDK base is REQUIRED (hub ruling 2026-08-18, same as
    # scholar/stats): the leaf is an SDK workspace app or it fails
    # loud with the install hint. No vanilla fallback — a fallback
    # would silently drop every SDK contract.
    import importlib.util

    # Act
    if importlib.util.find_spec("scitex_sdk") is None:
        with pytest.raises(ImportError, match="scitex-live-paper\\[server\\]"):
            import scitex_live_paper._django.apps  # noqa: F401
    else:
        from scitex_live_paper._django import apps as apps_mod
        from scitex_sdk import app as _sdk_app

        # Assert — stats/writer leaf shape through the package path
        assert issubclass(
            apps_mod.LivePaperConfig, _sdk_app.embed.ScitexAppConfig
        )


def test_manifest_carries_registry_required_fields():
    # Arrange
    manifest_path = SRC_ROOT / "_django" / "manifest.json"
    required = ("name", "slug", "label", "version", "icon")
    manifest = json.loads(manifest_path.read_text())
    # Act
    missing = [field for field in required if not manifest.get(field)]
    # Assert — same required set scitex_app validates on
    assert missing == []


def test_manifest_carries_mount_fields():
    # Arrange — hub generic plugin mount reads these (scholar/writer/
    # stats shape): scope + pip_package + mount_policy jail.
    manifest_path = SRC_ROOT / "_django" / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    # Act
    # Assert
    assert manifest.get("scope") in ("user", "project")
    assert manifest.get("pip_package") == "scitex-live-paper"
    policy = manifest.get("mount_policy")
    assert isinstance(policy, dict)
    assert policy.get("login_required") is True
    assert isinstance(policy.get("jail"), dict)


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
