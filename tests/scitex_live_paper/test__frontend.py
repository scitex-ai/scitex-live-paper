"""Public frontend package is wheel-contained and independent of Django startup."""

from __future__ import annotations

import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

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


@pytest.mark.parametrize("resource", [
    "_django/manifest.json", "_django/templates/live_paper/viewer.html",
    "_renderer/templates/paper.html.j2", "_renderer/assets/claims.css",
    "_renderer/assets/paper-panel.js", "_renderer/assets/mermaid/mermaid.min.js",
    "_renderer/assets/pdfjs/pdf.worker.min.mjs",
    "_django/static/live_paper/js/vendor/mermaid.min.js",
    "_django/static/live_paper/pdfjs/pdf.min.mjs",
])
def test_runtime_resources_exist_inside_the_actual_package(resource):
    # Arrange
    root = get_frontend_package_dir()
    # Act
    available = (root / resource).is_file()
    # Assert
    assert available, resource


def test_source_and_built_archives_preserve_all_runtime_resources(tmp_path):
    # Arrange
    source = Path(__file__).resolve().parents[2]
    package = source / "src/scitex_live_paper"
    expected = {
        str(path.relative_to(package)): path.read_bytes()
        for path in package.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
        and path.suffix not in {".py", ".pyc"}
    }
    dist = tmp_path / "dist"
    environment = {
        "PATH": str(Path(sys.executable).parent) + ":/usr/local/bin:/usr/bin:/bin",
        "HOME": str(tmp_path), "TMPDIR": str(tmp_path), "LANG": "C.UTF-8",
        "SCITEX_DIR": str(tmp_path / "scitex"),
        "PIP_CACHE_DIR": str(tmp_path / "pip-cache"),
    }
    # Act
    subprocess.run(
        [sys.executable, "-m", "build", "--outdir", str(dist), str(source)],
        cwd=tmp_path, env=environment, check=True, capture_output=True, timeout=120,
    )
    with zipfile.ZipFile(next(dist.glob("*.whl"))) as archive:
        wheel = {name: archive.read("scitex_live_paper/" + name)
                 for name in expected if "scitex_live_paper/" + name in archive.namelist()}
    with tarfile.open(next(dist.glob("*.tar.gz"))) as archive:
        prefix = archive.getmembers()[0].name + "/src/scitex_live_paper/"
        sdist = {name: archive.extractfile(prefix + name).read()
                 for name in expected if prefix + name in archive.getnames()}
    # Assert
    assert (wheel, sdist) == (expected, expected)
