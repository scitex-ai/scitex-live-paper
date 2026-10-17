"""STX-TQ tests for ``docs/demo/monday-mock.html`` (Monday looks-only mock).

The mock is a static, zero-dependency file for the Monday demo. These tests
pin its contract: the file exists, parses as HTML, carries the real
fixture claim ids + statuses + DOI, and references no external assets
(``file://``-safe). Content edits must keep these pins green.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

MOCK = Path(__file__).resolve().parents[2] / "docs" / "demo" / "monday-mock.html"

EXPECTED_IDS = (
    "claim_a1b2c3d4e5f6",
    "claim_f6e5d4c3b2a1",
    "claim_999888777666",
)


class _ParseCheck(HTMLParser):
    """Refuse-broken-HTML gate: records positions of parse errors."""

    def __init__(self) -> None:
        # Arrange
        super().__init__(convert_charrefs=True)
        # Act
        self.errors: list[str] = []

    def error(self, message: str) -> None:  # pragma: no cover - Py2 API
        # Assert
        self.errors.append(message)


def _read_mock() -> str:
    # Arrange
    assert MOCK.is_file(), f"mock missing: {MOCK}"
    # Act
    text = MOCK.read_text(encoding="utf-8")
    # Assert
    assert len(text) > 1000, "mock is suspiciously small"
    return text


def test_mock_parses_as_html() -> None:
    # Arrange
    text = _read_mock()
    parser = _ParseCheck()
    # Act
    parser.feed(text)
    parser.close()
    # Assert
    assert parser.errors == []


def test_mock_carries_real_fixture_claims_and_doi() -> None:
    # Arrange
    text = _read_mock()
    needles = (
        *EXPECTED_IDS,
        "10.7554/eLife.99999",
        "verified",
        "suspect",
        "registered",
    )
    # Act
    missing = [needle for needle in needles if needle not in text]
    # Assert
    assert missing == []


def test_mock_has_no_external_asset_refs() -> None:
    # Arrange
    text = _read_mock()
    # Act
    external = re.findall(
        r'<(?:script|img|link|iframe)[^>]*(?:src|href)\s*=\s*["\']https?://',
        text,
        re.IGNORECASE,
    )
    # Assert
    assert external == []
