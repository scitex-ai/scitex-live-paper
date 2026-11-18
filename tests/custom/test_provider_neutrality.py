"""live-paper stays provider-neutral: its source names no evidence provider.

Any evidence provider plugs in through the contract
(docs/evidence-provider-contract.md); naming a specific provider package in
live-paper's source or packaging fails this test.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "scitex_live_paper"

#: Specific evidence-provider packages live-paper must never name.
PROVIDER_PACKAGES = re.compile(r"scitex[_-]?clew|\bclew\b", re.IGNORECASE)
#: Third-party vendored bundles are not live-paper source.
VENDORED = ("assets/pdfjs/", "assets/mermaid/", "static/live_paper/pdfjs/", "/vendor/")
SOURCE_SUFFIXES = {
    ".py",
    ".js",
    ".mjs",
    ".css",
    ".j2",
    ".html",
    ".json",
    ".md",
    ".ts",
    ".toml",
    ".yaml",
}


def test_source_names_no_specific_provider():
    # Arrange
    files = [
        p
        for p in SRC.rglob("*")
        if p.is_file()
        and p.suffix in SOURCE_SUFFIXES
        and not any(v in p.relative_to(SRC).as_posix() for v in VENDORED)
    ]
    # Act
    offenders = [
        f"{p.relative_to(SRC)}:{n}: {line.strip()[:100]}"
        for p in files
        for n, line in enumerate(p.read_text(errors="replace").splitlines(), 1)
        if PROVIDER_PACKAGES.search(line)
    ]
    # Assert
    assert offenders == [], "live-paper must stay provider-neutral:\n" + "\n".join(
        offenders
    )


def test_pyproject_names_no_specific_provider():
    # Arrange
    pyproject = (ROOT / "pyproject.toml").read_text()
    # Act
    found = PROVIDER_PACKAGES.findall(pyproject)
    # Assert
    assert found == []
