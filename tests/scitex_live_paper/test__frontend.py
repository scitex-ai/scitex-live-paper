"""Public frontend package is wheel-contained and independent of Django startup."""

from __future__ import annotations

import json

from scitex_live_paper import get_frontend_package_dir


def test_frontend_package_exports_stay_inside_installed_root():
    # Arrange
    # Act
    root = get_frontend_package_dir()
    metadata = json.loads((root / "package.json").read_text())
    exports = metadata["exports"]["./pdf-provider"]
    # Assert
    assert all(
        (root / exports[kind]).resolve().is_relative_to(root)
        for kind in ("types", "import")
    )


def test_frontend_public_contract_is_explicit():
    # Arrange
    # Act
    root = get_frontend_package_dir()
    metadata = json.loads((root / "package.json").read_text())
    # Assert
    assert metadata["scitexRichPdfContract"] == "scitex-live-paper.rich-pdf/v1"


def test_public_provider_has_no_native_api_or_bundle_dependency():
    # Arrange
    # Act
    source = (
        get_frontend_package_dir() / "_django/static/live_paper/js/pdf-provider.js"
    ).read_text()
    # Assert
    assert all(
        fragment not in source
        for fragment in (
            "withBundleContext",
            "apiBase",
            "fetch(",
            "claim_id",
            "scitex_writer",
            "agentic_journal",
        )
    )


def test_native_page_loads_one_cache_coherent_entry():
    # Arrange
    # Act
    template = (
        get_frontend_package_dir() / "_django/templates/live_paper/viewer.html"
    ).read_text()
    # Assert
    assert "{% app_static 'live_paper/js/viewer-entry.js' %}" in template


def test_provider_styles_are_exported_and_present():
    # Arrange
    # Act
    root = get_frontend_package_dir()
    metadata = json.loads((root / "package.json").read_text())
    # Assert
    assert (root / metadata["exports"]["./pdf-provider.css"]).is_file()
